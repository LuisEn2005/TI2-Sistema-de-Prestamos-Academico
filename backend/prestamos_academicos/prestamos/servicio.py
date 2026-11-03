"""Casos de uso del contexto Préstamos (Sprint 3: RF10, RF11 y parte de RF13).

Un préstamo entrega uno o más ítems bajo una modalidad. La fecha límite sale de la política
definida para la combinación de perfil y modalidad (RN2); los cupos y los tipos de recurso
permitidos se aplican por perfil (RF03, RF13); la devolución registra la condición de cada
ítem y deja el recurso en el estado que corresponde. Todo ocurre en una sola transacción.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from ..configuracion_servicio import Modalidad, PoliticaServicio
from ..compartido import ErrorDominio
from ..identidad import Permiso, Usuario
from ..inventario import EstadoItem
from .dominio import CondicionDevolucion, EstadoPrestamo, Prestamo
from ..compartido import ItemId, ReservaId, RolUsuario, UsuarioId
from ..compartido import validacion as v
from ..compartido import Conflicto, ErrorAplicacion, NoEncontrado
from ..compartido.reloj import Reloj
from ..sanciones import Sancion
from ..calendario_laboral.servicio import CalendarioLaboralApplicationService
from ..configuracion_servicio.servicio import MODALIDAD_IN_SITU

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
    reservas_activas: int
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
        self.calendario = CalendarioLaboralApplicationService(fabrica_uow, self.reloj)

    # -- reglas compartidas por la previsualización y la entrega ---------------------------
    def _resolver_contexto(self, uow, usuario_id, modalidad_id, rol_solicitante) -> ContextoPrestamo:
        hoy = self.reloj.hoy()
        uow.sanciones.sincronizar_vencidas(hoy, self.reloj.ahora(), usuario_id)
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
        politica = uow.politicas.find_by_rol_y_modalidad(rol, modalidad_id)
        if politica is None:
            raise ErrorAplicacion(
                "El perfil no tiene una política para la modalidad seleccionada.", 422)

        try:
            dias = politica.diasPrestamo
            limite_base = Prestamo.calcularFechaLimite(hoy, dias)
            limite = self.calendario.siguiente_laborable(uow, limite_base)
        except ErrorDominio as e:
            raise ErrorAplicacion(str(e), 422)
        return ContextoPrestamo(
            usuario=usuario, rol=rol, politica=politica, modalidad=modalidad,
            items_en_prestamo=uow.prestamos.contar_items_activos(usuario_id),
            reservas_activas=uow.reservas.contar_activas_usuario(usuario_id),
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
                "fecha_inicio": self.reloj.hoy().isoformat(),
                "roles_posibles": [r.value for r in ctx.usuario.rolesPrestatarios()],
                "rol_solicitante": ctx.rol.value,
                "modalidad": ctx.modalidad.nombre,
                "dias_plazo": ctx.dias_plazo,
                "fecha_limite": ctx.fecha_limite.isoformat(),
                "max_items_simultaneos": ctx.politica.maxItemsSimultaneos,
                "items_en_prestamo": ctx.items_en_prestamo,
                "reservas_activas": ctx.reservas_activas,
                "cupo_ocupado": ctx.items_en_prestamo + ctx.reservas_activas,
                "cupo_restante": ctx.politica.cupoRestante(
                    ctx.items_en_prestamo + ctx.reservas_activas),
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
            "reserva_id": p.reservaId.valor if p.reservaId else None,
            "usuario_id": p.usuarioId.valor,
            "usuario": nombres.get(p.usuarioId.valor),
            "rol_solicitante": p.rolSolicitante.value if p.rolSolicitante else None,
            "modalidad": p.modalidadNombre,
            "dias_plazo": p.diasPlazo,
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
            vista = self._vistas(uow, [prestamo])[0]
            vista["aplazamientos"] = uow.prestamos.listar_aplazamientos(prestamo_id)
            return vista

    # -- entrega (RF10) ------------------------------------------------------------------------
    def _fecha_final(self, uow, ctx, fecha_fin):
        hoy = self.reloj.hoy()
        self.calendario.validar_laborable(uow, hoy, "fecha de entrega")
        fin = fecha_fin or ctx.fecha_limite
        self.calendario.validar_laborable(uow, fin, "fecha de devolución")
        if ctx.modalidad.nombre == MODALIDAD_IN_SITU:
            if fin != hoy:
                raise ErrorAplicacion("El préstamo in situ termina el mismo día.", 422)
            return fin, 1, 0
        transcurridos = (fin - hoy).days
        maximo_efectivo = (ctx.fecha_limite - hoy).days
        if transcurridos < 1 or transcurridos > maximo_efectivo:
            raise ErrorAplicacion(
                f"La fecha final debe estar entre mañana y {ctx.fecha_limite.isoformat()}.", 422)
        dias_base = min(transcurridos, ctx.politica.diasPrestamo)
        return fin, dias_base, transcurridos - dias_base

    def registrar(self, usuario_id, item_ids, modalidad_id, rol_solicitante=None,
                  fecha_fin=None):
        with self._uow() as uow:
            ctx = self._resolver_contexto(uow, usuario_id, modalidad_id, rol_solicitante)
            fin, dias_plazo, _ = self._fecha_final(uow, ctx, fecha_fin)
            uow.usuarios.bloquear(usuario_id)  # dos entregas simultáneas no superan el cupo
            ctx.items_en_prestamo = uow.prestamos.contar_items_activos(usuario_id)
            ctx.reservas_activas = uow.reservas.contar_activas_usuario(usuario_id)

            items = uow.items.find_by_ids(item_ids)
            faltan = [i for i in item_ids if i not in items]
            if faltan:
                raise NoEncontrado(f"No existe el recurso {faltan[0]}.")

            no_permitidos = [i.codigo for i in items.values() if not ctx.politica.permiteTipo(i.TIPO)]
            if no_permitidos:
                raise ErrorAplicacion(
                    f"La política del perfil {ctx.rol.value} no permite prestar: "
                    f"{', '.join(sorted(no_permitidos))}.", 422)

            ocupado = ctx.items_en_prestamo + ctx.reservas_activas
            cupo = ctx.politica.cupoRestante(ocupado)
            if len(item_ids) > cupo:
                raise ErrorAplicacion(
                    f"Supera el límite de la política: máximo {ctx.politica.maxItemsSimultaneos} "
                    f"recursos simultáneos; tiene {ctx.items_en_prestamo} prestados, "
                    f"{ctx.reservas_activas} reservados y pide "
                    f"{len(item_ids)}.", 422)

            ocupados = [f"{i.codigo} ({i.estado.value})" for i in items.values()
                        if not i.estaDisponible()]
            if ocupados:
                raise Conflicto(f"No están disponibles: {', '.join(sorted(ocupados))}.")

            for item_id in item_ids:
                ultima = uow.prestamos.ultima_devolucion_item(item_id)
                if ultima is not None:
                    disponible = self.calendario.siguiente_laborable(
                        uow, self.reloj.fecha_local(ultima) + timedelta(days=1))
                    if self.reloj.hoy() < disponible:
                        raise Conflicto(
                            f"El recurso {items[item_id].codigo} estará disponible el "
                            f"{disponible.isoformat()} después de su devolución.")
                if uow.reservas.find_pendientes_solapadas(
                        item_id, self.reloj.hoy(), fin):
                    raise Conflicto(
                        f"El recurso {items[item_id].codigo} tiene solicitudes pendientes "
                        "en ese rango; resuélvalas antes de registrar el préstamo.")
                if uow.reservas.find_confirmadas_solapadas(
                        item_id, self.reloj.hoy(), fin):
                    raise Conflicto(
                        f"El recurso {items[item_id].codigo} tiene una reserva confirmada "
                        "dentro del rango solicitado.")

            # Orden fijo por id: evita bloqueos cruzados entre entregas concurrentes en PostgreSQL.
            for item_id in sorted(item_ids):
                if not uow.items.cambiar_estado_si(
                        item_id, EstadoItem.DISPONIBLE, EstadoItem.PRESTADO):
                    raise Conflicto(
                        f"El recurso {items[item_id].codigo} dejó de estar disponible.")

            try:
                prestamo = Prestamo.entregar(
                    usuarioId=UsuarioId(usuario_id), politicaId=ctx.politica.id,
                    rol=ctx.rol, modalidadId=ctx.modalidad.id,
                    modalidadNombre=ctx.modalidad.nombre, diasPlazo=dias_plazo,
                    items=[ItemId(i) for i in item_ids], ahora=self.reloj.ahora(),
                    hoy=self.reloj.hoy())
                prestamo.fechaDevolucionEsperada = fin
            except ErrorDominio as e:
                raise ErrorAplicacion(str(e), 422)
            guardado = uow.prestamos.save(prestamo)
            vista = self._vistas(uow, [guardado])[0]
            uow.commit()
        return vista

    # -- conversión de reserva (RF09) ----------------------------------------------------------
    def registrar_desde_reserva(self, actor, reserva_id, modalidad_id=None, fecha_fin=None):
        from ..reservas import EstadoReserva

        with self._uow() as uow:
            reserva = uow.reservas.find_by_id(reserva_id)
            if reserva is None:
                raise NoEncontrado("La reserva no existe.")
            if reserva.estado != EstadoReserva.CONFIRMADA:
                raise Conflicto("Solo una reserva confirmada puede convertirse en préstamo.")
            if reserva.fechaInicio != self.reloj.hoy():
                raise Conflicto("La reserva solo puede entregarse en su fecha de inicio.")

            usuario_id = reserva.usuarioId.valor
            item_id = reserva.itemId.valor
            modalidad_id = modalidad_id or (
                reserva.modalidadId.valor if reserva.modalidadId else None)
            if modalidad_id is None:
                raise ErrorAplicacion(
                    "La reserva heredada no tiene modalidad; indique una para la entrega.", 400)
            if reserva.modalidadId and modalidad_id != reserva.modalidadId.valor:
                raise ErrorAplicacion("La modalidad debe coincidir con la reserva.", 422)
            ctx = self._resolver_contexto(uow, usuario_id, modalidad_id,
                                          reserva.rolSolicitante.value)
            uow.usuarios.bloquear(usuario_id)
            items_en_prestamo = uow.prestamos.contar_items_activos(usuario_id)
            reservas_activas = uow.reservas.contar_activas_usuario(usuario_id)
            if items_en_prestamo + reservas_activas > ctx.politica.maxItemsSimultaneos:
                raise ErrorAplicacion(
                    f"El usuario supera el cupo compartido de "
                    f"{ctx.politica.maxItemsSimultaneos} recursos.", 422)
            item = uow.items.find_by_id(item_id)
            if item is None:
                raise NoEncontrado("El recurso de la reserva no existe.")
            if not ctx.politica.permiteTipo(item.TIPO):
                raise ErrorAplicacion(
                    f"La política del perfil {ctx.rol.value} ya no permite {item.codigo}.", 422)
            fin = fecha_fin or reserva.fechaFin
            if fin > reserva.fechaFin or fin < reserva.fechaInicio:
                raise ErrorAplicacion("La entrega solo puede mantener o acortar el rango.", 422)
            self.calendario.validar_laborable(uow, fin, "fecha de devolución")
            if not uow.items.cambiar_estado_si(
                    item_id, EstadoItem.DISPONIBLE, EstadoItem.PRESTADO):
                raise Conflicto("El recurso de la reserva no está disponible físicamente.")

            try:
                dias_transcurridos = (1 if fin == self.reloj.hoy()
                                      else (fin - self.reloj.hoy()).days)
                dias_base = min(dias_transcurridos, ctx.politica.diasPrestamo)
                prestamo = Prestamo.entregar(
                    usuarioId=UsuarioId(usuario_id), politicaId=ctx.politica.id,
                    rol=ctx.rol, modalidadId=ctx.modalidad.id,
                    modalidadNombre=ctx.modalidad.nombre,
                    diasPlazo=dias_base,
                    items=[ItemId(item_id)], ahora=self.reloj.ahora(), hoy=self.reloj.hoy())
                prestamo.fechaDevolucionEsperada = fin
                prestamo.reservaId = ReservaId(reserva_id)
                reserva.convertir()
            except ErrorDominio as error:
                raise ErrorAplicacion(str(error), 422)
            guardado = uow.prestamos.save(prestamo)
            uow.reservas.save(reserva)
            uow.reservas.registrar_evento(
                reserva.id.valor, "ENTREGADA", self.reloj.ahora(),
                actor_id=actor.id.valor, motivo="Préstamo creado desde la reserva.")
            vista = self._vistas(uow, [guardado])[0]
            uow.commit()
        return vista

    # -- devolución (RF11) -----------------------------------------------------------------------
    def devolver(self, prestamo_id, condiciones):
        """`condiciones`: lista de {item_id, condicion, observacion?} que cubre todos los ítems."""
        pedidas, observaciones = self._leer_condiciones(condiciones)
        with self._uow() as uow:
            self.calendario.validar_laborable(
                uow, self.reloj.hoy(), "fecha de devolución")
            prestamo = uow.prestamos.find_by_id(prestamo_id)
            if prestamo is None:
                raise NoEncontrado("El préstamo no existe.")
            hoy = self.reloj.hoy()
            dias_atraso = prestamo.diasAtraso(hoy)
            try:
                prestamo.registrarDevolucion(
                    pedidas, hoy=hoy, fecha=self.reloj.ahora(),
                    observaciones=observaciones)
            except ErrorDominio as e:
                raise Conflicto(str(e)) if "ya fue devuelto" in str(e) else ErrorAplicacion(str(e), 422)

            for detalle in sorted(prestamo.detalles, key=lambda d: d.itemId.valor):
                destino = ESTADO_TRAS_DEVOLUCION[detalle.condicion]
                if not uow.items.cambiar_estado_si(detalle.itemId.valor, EstadoItem.PRESTADO, destino):
                    raise Conflicto(
                        "Un recurso del préstamo no figura como prestado; revise su estado.")
                self.calendario.procesar_devolucion(
                    uow, detalle.itemId.valor,
                    disponible=destino == EstadoItem.DISPONIBLE)
            guardado = uow.prestamos.save(prestamo)
            vista = self._vistas(uow, [guardado])[0]
            if dias_atraso > 0:
                politica = (uow.politicas.find_by_id(prestamo.politicaServicioId.valor)
                            if prestamo.politicaServicioId else None)
                factor = politica.diasSancionPorDiaAtraso if politica else 1
                sancion = uow.sanciones.save(Sancion.porAtraso(
                    usuario_id=prestamo.usuarioId.valor, prestamo_id=prestamo.id.valor,
                    dias_atraso=dias_atraso, factor=factor, hoy=hoy))
                uow.sanciones.actualizar_cache_usuario(prestamo.usuarioId.valor)
                vista["sancion_generada_id"] = sancion.id.valor
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
