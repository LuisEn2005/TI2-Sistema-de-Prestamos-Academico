"""Casos de uso de sanciones (RF14-RF16)."""

from decimal import Decimal, InvalidOperation

from .dominio import EstadoSancion, Monto, OrigenSancion, Sancion
from ..compartido import ErrorDominio, ErrorAplicacion, NoEncontrado, Conflicto
from ..compartido.reloj import Reloj
from ..identidad import Permiso

# Condición con que volvió el recurso -> origen de la sanción que le corresponde.
ORIGEN_POR_CONDICION = {"DANADO": OrigenSancion.DANO, "PERDIDO": OrigenSancion.PERDIDA}


class SancionApplicationService:
    def __init__(self, fabrica_uow, identidad, reloj=None):
        self._uow = fabrica_uow
        self._identidad = identidad
        self.reloj = reloj or Reloj()

    def _ve_todo(self, actor):
        return Permiso.CONSULTAR_HISTORIAL_GLOBAL in self._identidad.permisos_de(actor)

    @staticmethod
    def _vista(sancion, nombres, items=None):
        item = (items or {}).get(sancion.itemId.valor) if sancion.itemId else None
        return {
            "id": sancion.id.valor,
            "usuario_id": sancion.usuarioId.valor,
            "usuario": nombres.get(sancion.usuarioId.valor),
            "prestamo_id": sancion.prestamoId.valor if sancion.prestamoId else None,
            "item_id": sancion.itemId.valor if sancion.itemId else None,
            "recurso": f"{item.codigo} · {item.nombre}" if item else None,
            "origen": sancion.origen.value,
            "motivo": sancion.motivo,
            "monto": (format(sancion.monto.cantidad, ".2f") if sancion.monto else None),
            "moneda": sancion.monto.moneda if sancion.monto else None,
            "fecha_inicio": sancion.fechaInicio.isoformat(),
            "fecha_fin": sancion.fechaFin.isoformat() if sancion.fechaFin else None,
            "estado": sancion.estado.value,
            "resolucion": sancion.resolucion,
        }

    def listar(self, actor, estado=None):
        with self._uow() as uow:
            usuario_id = None if self._ve_todo(actor) else actor.id.valor
            uow.sanciones.sincronizar_vencidas(
                self.reloj.hoy(), self.reloj.ahora(), usuario_id)
            sanciones = uow.sanciones.listar(usuario_id=usuario_id, estado=estado)
            nombres = uow.usuarios.nombres_de([s.usuarioId.valor for s in sanciones])
            items = uow.items.find_by_ids([s.itemId.valor for s in sanciones if s.itemId])
            vistas = [self._vista(s, nombres, items) for s in sanciones]
            uow.commit()
        return vistas

    @staticmethod
    def _monto(valor):
        if valor in (None, ""):
            return None
        if isinstance(valor, bool):
            raise ErrorAplicacion("El monto debe ser un número positivo.", 400)
        try:
            cantidad = Decimal(str(valor)).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            raise ErrorAplicacion("El monto debe ser un número positivo.", 400)
        if (not cantidad.is_finite() or cantidad <= 0
                or cantidad > Decimal("99999999.99")):
            raise ErrorAplicacion("El monto debe estar entre 0.01 y 99999999.99.", 400)
        return Monto(cantidad, "PEN")

    @staticmethod
    def _ya_vinculados(uow, usuario_id):
        return {(s.prestamoId.valor, s.itemId.valor)
                for s in uow.sanciones.listar(usuario_id=usuario_id) if s.itemId}

    def recursos_sancionables(self, usuario_id):
        """Recursos que el usuario devolvió dañados o perdidos y aún no tienen sanción."""
        with self._uow() as uow:
            if uow.usuarios.find_by_id(usuario_id) is None:
                raise NoEncontrado("El usuario no existe.")
            vinculados = self._ya_vinculados(uow, usuario_id)
            filas = [f for f in uow.prestamos.devoluciones_con_incidencia(usuario_id)
                     if (f.prestamo_id, f.item_id) not in vinculados]
            items = uow.items.find_by_ids([f.item_id for f in filas])
            return [{
                "prestamo_id": f.prestamo_id, "item_id": f.item_id,
                "codigo": items[f.item_id].codigo, "nombre": items[f.item_id].nombre,
                "condicion": f.condicion, "observacion": f.observacion,
                "origen": ORIGEN_POR_CONDICION[f.condicion].value,
                "fecha_devolucion": (self.reloj.fecha_local(f.fecha_devolucion).isoformat()
                                     if f.fecha_devolucion else None),
            } for f in filas]

    @staticmethod
    def _origen_del_recurso(uow, prestamo, item_id, usuario_id):
        """El origen sale de la condición con que se devolvió el recurso: no se elige."""
        detalle = next((d for d in prestamo.detalles if d.itemId.valor == item_id), None)
        if detalle is None:
            raise ErrorAplicacion("El recurso no pertenece a ese préstamo.", 422)
        condicion = detalle.condicion.value if detalle.condicion else None
        if condicion not in ORIGEN_POR_CONDICION:
            raise ErrorAplicacion("El recurso no se devolvió dañado ni perdido.", 422)
        if (prestamo.id.valor, item_id) in SancionApplicationService._ya_vinculados(
                uow, usuario_id):
            raise Conflicto("Ese recurso ya tiene una sanción registrada.")
        return ORIGEN_POR_CONDICION[condicion]

    def registrar_manual(self, actor, *, usuario_id, prestamo_id, item_id, motivo,
                         dias=None, monto=None):
        """Sanción por daño o pérdida de un recurso concreto (RF15)."""
        if dias is not None and (type(dias) is not int or not 1 <= dias <= 365):
            raise ErrorAplicacion("Los días deben estar entre 1 y 365.", 400)
        if prestamo_id is None or item_id is None:
            raise ErrorAplicacion(
                "Indique el recurso dañado o perdido («prestamo_id» e «item_id»).", 400)
        with self._uow() as uow:
            usuario = uow.usuarios.find_by_id(usuario_id)
            if usuario is None:
                raise NoEncontrado("El usuario no existe.")
            if not usuario.esPrestatario():
                raise ErrorAplicacion("El usuario no tiene un perfil prestatario.", 422)
            prestamo = uow.prestamos.find_by_id(prestamo_id)
            if prestamo is None:
                raise NoEncontrado("El préstamo no existe.")
            if prestamo.usuarioId.valor != usuario_id:
                raise ErrorAplicacion("El préstamo no pertenece al usuario.", 422)
            origen = self._origen_del_recurso(uow, prestamo, item_id, usuario_id)
            inicio = Sancion.inicioEncadenado(
                self.reloj.hoy(), uow.sanciones.fin_ultima_activa(usuario_id))
            try:
                sancion = Sancion.manual(
                    usuario_id=usuario_id, actor_id=actor.id.valor,
                    origen=origen, motivo=motivo, hoy=inicio,
                    dias=dias, monto=self._monto(monto), prestamo_id=prestamo_id,
                    item_id=item_id)
            except ErrorDominio as error:
                raise ErrorAplicacion(str(error), 422)
            guardada = uow.sanciones.save(sancion)
            uow.sanciones.actualizar_cache_usuario(usuario_id)
            vista = self._vista(guardada, {usuario_id: usuario.nombre},
                                uow.items.find_by_ids([item_id]))
            uow.commit()
        return vista

    def cerrar(self, sancion_id, resolucion, actor=None):
        with self._uow() as uow:
            sancion = uow.sanciones.find_by_id(sancion_id)
            if sancion is None:
                raise NoEncontrado("La sanción no existe.")
            try:
                sancion.cerrar(resolucion, self.reloj.ahora(),
                               por=actor.id if actor is not None else None)
            except ErrorDominio as error:
                raise Conflicto(str(error))
            guardada = uow.sanciones.save(sancion)
            uow.sanciones.actualizar_cache_usuario(sancion.usuarioId.valor)
            nombre = uow.usuarios.nombres_de([sancion.usuarioId.valor])
            items = uow.items.find_by_ids([sancion.itemId.valor] if sancion.itemId else [])
            vista = self._vista(guardada, nombre, items)
            uow.commit()
        return vista
