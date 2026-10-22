"""Casos de uso del contexto Préstamos (Sprint 3: RF10, RF11 y parte de RF13).

Un préstamo entrega uno o más ítems bajo una modalidad. La fecha límite sale de la modalidad
y de la política del perfil con que se presta (RN2); los cupos y los tipos de recurso
permitidos se aplican por perfil (RF03, RF13); la devolución registra la condición de cada
ítem y deja el recurso en el estado que corresponde. Todo ocurre en una sola transacción.
"""

from dataclasses import dataclass
from typing import Optional

from ..dominio.configuracion import Modalidad, PoliticaServicio
from ..dominio.errores import ErrorDominio
from ..dominio.identidad import Permiso, Usuario
from ..dominio.inventario import EstadoItem
from ..dominio.prestamos import CondicionDevolucion, EstadoPrestamo, Prestamo
from ..dominio.shared_kernel import ItemId, RolUsuario, UsuarioId
from . import validacion as v
from .errores import Conflicto, ErrorAplicacion, NoEncontrado, SinPermiso
from .reloj import Reloj

MAX_ITEMS_POR_PRESTAMO = 50
MAX_OBSERVACION = 300

# Estado en que queda el recurso según la condición con que vuelve.
ESTADO_TRAS_DEVOLUCION = {
    CondicionDevolucion.BUEN_ESTADO: EstadoItem.DISPONIBLE,
    CondicionDevolucion.DANADO: EstadoItem.EN_MANTENIMIENTO,   # requiere revisión antes de prestarse
    CondicionDevolucion.PERDIDO: EstadoItem.EXTRAVIADO,
}


@dataclass
class ContextoPrestamo:
    """Datos que fijan las reglas de un préstamo: quién, con qué perfil, bajo qué modalidad."""
    usuario: Usuario
    rol: RolUsuario
    politica: PoliticaServicio
    modalidad: Modalidad
    items_en_prestamo: int
    dias_plazo: int
    fecha_limite: object


def _iso(fecha):
    if fecha is None:
        return None
    if fecha.tzinfo is None:
        from datetime import timezone
        fecha = fecha.replace(tzinfo=timezone.utc)
    return fecha.isoformat()


class PrestamoApplicationService:
    def __init__(self, fabrica_uow, identidad, reloj: Optional[Reloj] = None):
        self._uow = fabrica_uow
        self._identidad = identidad
        self.reloj = reloj or Reloj()

    # -- reglas compartidas por la previsualización y la entrega ---------------------------
    def _resolver_contexto(self, uow, usuario_id, modalidad_id, rol_solicitante) -> ContextoPrestamo:
        usuario = uow.usuarios.find_by_id(usuario_id)
        if usuario is None:
            raise NoEncontrado("El usuario no existe.")
        motivo = usuario.motivoNoHabilitado()
        if motivo:
            raise ErrorAplicacion(motivo, 422)

        modalidad = uow.modalidades.find_by_id(modalidad_id)
        if modalidad is None:
            raise NoEncontrado("La modalidad no existe.")
        if not modalidad.activo:
            raise ErrorAplicacion(f"La modalidad «{modalidad.nombre}» no está activa.", 422)

        rol = self._elegir_rol(usuario, rol_solicitante)
        politica_id = usuario.politicaIdPara(rol)
        politica = uow.politicas.find_by_id(politica_id.valor) if politica_id else None
        if politica is None:
            raise ErrorAplicacion("El perfil del usuario no tiene una política de servicio.", 422)

        hoy = self.reloj.hoy()
        try:
            snapshot = modalidad.snapshot()
            dias = snapshot.diasEfectivos(politica.diasPrestamoDefault)
            limite = Prestamo(modalidad=snapshot).calcularFechaLimite(hoy, politica.diasPrestamoDefault)
        except ErrorDominio as e:
            raise ErrorAplicacion(str(e), 422)
        return ContextoPrestamo(
            usuario=usuario, rol=rol, politica=politica, modalidad=modalidad,
            items_en_prestamo=uow.prestamos.contar_items_activos(usuario_id),
            dias_plazo=dias, fecha_limite=limite)

    @staticmethod
    def _elegir_rol(usuario, rol_solicitante):
        posibles = usuario.rolesPrestatarios()
        if rol_solicitante is not None:
            try:
                rol = RolUsuario(rol_solicitante)
            except ValueError:
                raise ErrorAplicacion(f"Rol desconocido: {rol_solicitante!r}.", 400)
            if rol not in posibles:
                raise ErrorAplicacion(
                    f"El usuario no tiene el perfil {rol.value} para recibir préstamos.", 422)
        elif len(posibles) == 1:
            rol = posibles[0]
        else:
            nombres = ", ".join(r.value for r in posibles)
            raise ErrorAplicacion(
                f"El usuario tiene varios perfiles ({nombres}): indique con cuál presta.", 400)
        if not usuario.vinculacionVigentePara(rol):
            raise ErrorAplicacion(
                f"El usuario no tiene vinculación vigente como {rol.value}.", 422)
        return rol

    def condiciones(self, usuario_id, modalidad_id, rol_solicitante=None):
        """Previsualiza plazo y cupo con las mismas reglas que aplicará la entrega."""
        with self._uow() as uow:
            usuario = uow.usuarios.find_by_id(usuario_id)
            if usuario is None:
                raise NoEncontrado("El usuario no existe.")
            motivo = usuario.motivoNoHabilitado()
            if motivo:
                raise ErrorAplicacion(motivo, 422)
            if rol_solicitante is None and len(usuario.rolesPrestatarios()) > 1:
                # La interfaz debe pedir el perfil antes de poder calcular plazo y cupo.
                return {"usuario_id": usuario_id, "rol_solicitante": None,
                        "roles_posibles": [r.value for r in usuario.rolesPrestatarios()]}
            ctx = self._resolver_contexto(uow, usuario_id, modalidad_id, rol_solicitante)
            return {
                "usuario_id": usuario_id,
                "roles_posibles": [r.value for r in ctx.usuario.rolesPrestatarios()],
                "rol_solicitante": ctx.rol.value,
                "modalidad": ctx.modalidad.nombre,
                "dias_plazo": ctx.dias_plazo,
                "fecha_limite": ctx.fecha_limite.isoformat(),
                "max_items_simultaneos": ctx.politica.maxItemsSimultaneos,
                "items_en_prestamo": ctx.items_en_prestamo,
                "cupo_restante": ctx.politica.cupoRestante(ctx.items_en_prestamo),
                "tipos_permitidos": ctx.politica.tiposPermitidos(),
            }

    # -- consulta ----------------------------------------------------------------------------
    def _vistas(self, uow, prestamos):
        nombres = uow.usuarios.nombres_de([p.usuarioId.valor for p in prestamos])
        items = uow.items.find_by_ids(
            [d.itemId.valor for p in prestamos for d in p.detalles])
        hoy = self.reloj.hoy()
        return [self._vista(p, nombres, items, hoy) for p in prestamos]

    def _vista(self, p, nombres, items, hoy):
        devuelto = p.estado == EstadoPrestamo.DEVUELTO
        if devuelto:
            atraso = max(0, (self.reloj.fecha_local(p.fechaDevolucionReal)
                             - p.fechaDevolucionEsperada).days) if p.fechaDevolucionEsperada else 0
        else:
            atraso = p.diasAtraso(hoy)
        return {
            "id": p.id.valor,
            "usuario_id": p.usuarioId.valor,
            "usuario": nombres.get(p.usuarioId.valor),
            "rol_solicitante": p.rolSolicitante.value if p.rolSolicitante else None,
            "modalidad": p.modalidad.nombre if p.modalidad else None,
            "dias_plazo": p.modalidad.diasPlazo if p.modalidad else None,
            "items": [{
                "item_id": d.itemId.valor,
                "codigo": items[d.itemId.valor].codigo,
                "nombre": items[d.itemId.valor].nombre,
                "tipo": items[d.itemId.valor].TIPO,
                "condicion": d.condicion.value if d.condicion else None,
                "observacion": d.observacion,
            } for d in p.detalles],
            "fecha_prestamo": _iso(p.fechaEntrega),
            "fecha_limite": p.fechaDevolucionEsperada.isoformat() if p.fechaDevolucionEsperada else None,
            "fecha_devolucion": _iso(p.fechaDevolucionReal),
            "estado": "devuelto" if devuelto else "activo",
            "vencido": p.estaVencido(hoy),
            "dias_atraso": atraso,
        }

    def _ve_todo(self, actor):
        return Permiso.REGISTRAR_ENTREGA_PRESTAMO in self._identidad.permisos_de(actor)

    def listar(self, actor, *, estado=None, pagina=1, limite=20):
        """Un gestor ve todos los préstamos; los demás, solo los propios."""
        with self._uow() as uow:
            prestamos, total = uow.prestamos.buscar(
                usuario_id=None if self._ve_todo(actor) else actor.id.valor,
                estado=estado, hoy=self.reloj.hoy(), pagina=pagina, limite=limite)
            return {"prestamos": self._vistas(uow, prestamos), "total": total,
                    "pagina": pagina, "limite": limite}

    def obtener(self, actor, prestamo_id):
        with self._uow() as uow:
            prestamo = uow.prestamos.find_by_id(prestamo_id)
            if prestamo is None or (not self._ve_todo(actor)
                                    and prestamo.usuarioId.valor != actor.id.valor):
                raise NoEncontrado("El préstamo no existe.")
            return self._vistas(uow, [prestamo])[0]

    # -- entrega (RF10) ------------------------------------------------------------------------
    def registrar(self, usuario_id, item_ids, modalidad_id, rol_solicitante=None):
        with self._uow() as uow:
            ctx = self._resolver_contexto(uow, usuario_id, modalidad_id, rol_solicitante)
            uow.usuarios.bloquear(usuario_id)  # dos entregas simultáneas no superan el cupo
            ctx.items_en_prestamo = uow.prestamos.contar_items_activos(usuario_id)

            items = uow.items.find_by_ids(item_ids)
            faltan = [i for i in item_ids if i not in items]
            if faltan:
                raise NoEncontrado(f"No existe el recurso {faltan[0]}.")

            no_permitidos = [i.codigo for i in items.values() if not ctx.politica.permiteTipo(i.TIPO)]
            if no_permitidos:
                raise ErrorAplicacion(
                    f"La política del perfil {ctx.rol.value} no permite prestar: "
                    f"{', '.join(sorted(no_permitidos))}.", 422)

            cupo = ctx.politica.cupoRestante(ctx.items_en_prestamo)
            if len(item_ids) > cupo:
                raise ErrorAplicacion(
                    f"Supera el límite de la política: máximo {ctx.politica.maxItemsSimultaneos} "
                    f"ítems simultáneos, tiene {ctx.items_en_prestamo} en préstamo y pide "
                    f"{len(item_ids)}.", 422)

            ocupados = [f"{i.codigo} ({i.estado.value})" for i in items.values()
                        if not i.estaDisponible()]
            if ocupados:
                raise Conflicto(f"No están disponibles: {', '.join(sorted(ocupados))}.")

            # Orden fijo por id: evita bloqueos cruzados entre entregas concurrentes en PostgreSQL.
            for item_id in sorted(item_ids):
                if not uow.items.cambiar_estado_si(
                        item_id, EstadoItem.DISPONIBLE, EstadoItem.PRESTADO):
                    raise Conflicto(
                        f"El recurso {items[item_id].codigo} dejó de estar disponible.")

            try:
                prestamo = Prestamo.entregar(
                    usuarioId=UsuarioId(usuario_id), rol=ctx.rol, modalidad=ctx.modalidad.snapshot(),
                    diasPolitica=ctx.politica.diasPrestamoDefault,
                    items=[ItemId(i) for i in item_ids], ahora=self.reloj.ahora(),
                    hoy=self.reloj.hoy())
            except ErrorDominio as e:
                raise ErrorAplicacion(str(e), 422)
            guardado = uow.prestamos.save(prestamo)
            vista = self._vistas(uow, [guardado])[0]
            uow.commit()
        return vista

    # -- devolución (RF11) -----------------------------------------------------------------------
    def devolver(self, prestamo_id, condiciones):
        """`condiciones`: lista de {item_id, condicion, observacion?} que cubre todos los ítems."""
        pedidas, observaciones = self._leer_condiciones(condiciones)
        with self._uow() as uow:
            prestamo = uow.prestamos.find_by_id(prestamo_id)
            if prestamo is None:
                raise NoEncontrado("El préstamo no existe.")
            try:
                prestamo.registrarDevolucion(
                    pedidas, hoy=self.reloj.hoy(), fecha=self.reloj.ahora(),
                    observaciones=observaciones)
            except ErrorDominio as e:
                raise Conflicto(str(e)) if "ya fue devuelto" in str(e) else ErrorAplicacion(str(e), 422)

            for detalle in sorted(prestamo.detalles, key=lambda d: d.itemId.valor):
                destino = ESTADO_TRAS_DEVOLUCION[detalle.condicion]
                if not uow.items.cambiar_estado_si(detalle.itemId.valor, EstadoItem.PRESTADO, destino):
                    raise Conflicto(
                        "Un recurso del préstamo no figura como prestado; revise su estado.")
            guardado = uow.prestamos.save(prestamo)
            vista = self._vistas(uow, [guardado])[0]
            uow.commit()
        return vista

    @staticmethod
    def _leer_condiciones(condiciones):
        if not isinstance(condiciones, list) or not condiciones:
            raise ErrorAplicacion("Indique la condición de cada ítem devuelto («condiciones»).", 400)
        pedidas, observaciones = {}, {}
        for entrada in condiciones:
            entrada = v.objeto(entrada, "cada condición")
            v.campos(entrada, {"item_id", "condicion", "observacion"}, "cada condición")
            item_id = entrada.get("item_id")
            if type(item_id) is not int or item_id < 1:
                raise ErrorAplicacion("«item_id» debe ser un entero positivo.", 400)
            if item_id in pedidas:
                raise ErrorAplicacion(f"El ítem {item_id} aparece más de una vez.", 400)
            try:
                pedidas[item_id] = CondicionDevolucion(str(entrada.get("condicion")).upper())
            except ValueError:
                validas = ", ".join(c.value for c in CondicionDevolucion)
                raise ErrorAplicacion(f"Condición no válida. Use: {validas}.", 400)
            observacion = v.texto(entrada, "observacion", obligatorio=False, maximo=MAX_OBSERVACION)
            if observacion:
                observaciones[item_id] = observacion
        return pedidas, observaciones
