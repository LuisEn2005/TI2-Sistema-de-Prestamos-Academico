"""Casos de uso del contexto Préstamos (MVP del Sprint 1 integrado con identidad e inventario).

La fecha límite, modalidades, varios ítems y condición de devolución llegan en el Sprint 3.
"""

from ..dominio.errores import ErrorDominio
from ..dominio.identidad import Permiso
from ..dominio.inventario import EstadoItem
from ..dominio.prestamos import EstadoPrestamo, Prestamo
from ..dominio.prestamos.DetallePrestamo import DetallePrestamo
from ..dominio.shared_kernel import ItemId, UsuarioId
from .errores import Conflicto, ErrorAplicacion, NoEncontrado, SinPermiso


def _iso(fecha):
    if fecha is None:
        return None
    if fecha.tzinfo is None:
        from datetime import timezone
        fecha = fecha.replace(tzinfo=timezone.utc)
    return fecha.isoformat()


class PrestamoApplicationService:
    def __init__(self, fabrica_uow, identidad):
        self._uow = fabrica_uow
        self._identidad = identidad

    def _vista(self, uow, prestamo, cache):
        uid = prestamo.usuarioId.valor
        iid = prestamo.detalles[0].itemId.valor
        if ("u", uid) not in cache:
            cache[("u", uid)] = uow.usuarios.find_by_id(uid)
        if ("i", iid) not in cache:
            cache[("i", iid)] = uow.items.find_by_id(iid)
        usuario, item = cache[("u", uid)], cache[("i", iid)]
        return {
            "id": prestamo.id.valor,
            "usuario_id": uid,
            "usuario": usuario.nombre,
            "item_id": iid,
            "item": item.nombre,
            "codigo": item.codigo,
            "fecha_prestamo": _iso(prestamo.fechaEntrega),
            "fecha_devolucion": _iso(prestamo.fechaDevolucionReal),
            "estado": "activo" if prestamo.estado == EstadoPrestamo.ACTIVO else "devuelto",
        }

    def listar(self, actor):
        """Un gestor ve todos los préstamos; los demás, solo los propios."""
        ve_todo = Permiso.REGISTRAR_ENTREGA_PRESTAMO in self._identidad.permisos_de(actor)
        with self._uow() as uow:
            prestamos = uow.prestamos.listar(None if ve_todo else actor.id.valor)
            cache = {}
            return [self._vista(uow, p, cache) for p in prestamos]

    def registrar(self, usuario_id, item_id):
        with self._uow() as uow:
            usuario = uow.usuarios.find_by_id(usuario_id)
            if usuario is None:
                raise NoEncontrado("El usuario no existe.")
            motivo = usuario.motivoNoHabilitado()
            if motivo:
                raise ErrorAplicacion(motivo, 422)

            item = uow.items.find_by_id(item_id)
            if item is None:
                raise NoEncontrado("El recurso no existe.")
            try:
                item.marcarPrestado()
            except ErrorDominio:
                raise Conflicto(f"El recurso no está disponible (estado {item.estado.value}).")
            if not uow.items.cambiar_estado_si(item_id, EstadoItem.DISPONIBLE, EstadoItem.PRESTADO):
                raise Conflicto("El recurso ya no está disponible.")

            prestamo = uow.prestamos.save(Prestamo(
                usuarioId=UsuarioId(usuario_id),
                detalles=[DetallePrestamo(itemId=ItemId(item_id))]))
            vista = self._vista(uow, prestamo, {})
            uow.commit()
        return vista

    def devolver(self, prestamo_id):
        with self._uow() as uow:
            prestamo = uow.prestamos.find_by_id(prestamo_id)
            if prestamo is None:
                raise NoEncontrado("El préstamo no existe.")
            try:
                prestamo.registrarDevolucion()
            except ErrorDominio as e:
                raise Conflicto(str(e))
            item_id = prestamo.detalles[0].itemId.valor
            if not uow.items.cambiar_estado_si(item_id, EstadoItem.PRESTADO, EstadoItem.DISPONIBLE):
                raise Conflicto("El recurso no figura como prestado; revise su estado.")
            guardado = uow.prestamos.save(prestamo)
            vista = self._vista(uow, guardado, {})
            uow.commit()
        return vista
