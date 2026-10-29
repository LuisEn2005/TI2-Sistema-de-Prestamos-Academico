"""Casos de uso de sanciones (RF14-RF16)."""

from decimal import Decimal, InvalidOperation

from .dominio import EstadoSancion, Monto, OrigenSancion, Sancion
from ..compartido import ErrorDominio, ErrorAplicacion, NoEncontrado, Conflicto
from ..compartido.reloj import Reloj
from ..identidad import Permiso


class SancionApplicationService:
    def __init__(self, fabrica_uow, identidad, reloj=None):
        self._uow = fabrica_uow
        self._identidad = identidad
        self.reloj = reloj or Reloj()

    def _ve_todo(self, actor):
        return Permiso.CONSULTAR_HISTORIAL_GLOBAL in self._identidad.permisos_de(actor)

    @staticmethod
    def _vista(sancion, nombres):
        return {
            "id": sancion.id.valor,
            "usuario_id": sancion.usuarioId.valor,
            "usuario": nombres.get(sancion.usuarioId.valor),
            "prestamo_id": sancion.prestamoId.valor if sancion.prestamoId else None,
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
            vistas = [self._vista(s, nombres) for s in sanciones]
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

    def registrar_manual(self, actor, *, usuario_id, origen, motivo,
                         dias=None, monto=None, prestamo_id=None):
        if dias is not None and (type(dias) is not int or not 1 <= dias <= 365):
            raise ErrorAplicacion("Los días deben estar entre 1 y 365.", 400)
        try:
            origen = OrigenSancion(str(origen).upper())
        except ValueError:
            raise ErrorAplicacion("El origen debe ser DANO o PERDIDA.", 400)
        with self._uow() as uow:
            usuario = uow.usuarios.find_by_id(usuario_id)
            if usuario is None:
                raise NoEncontrado("El usuario no existe.")
            if not usuario.esPrestatario():
                raise ErrorAplicacion("El usuario no tiene un perfil prestatario.", 422)
            if prestamo_id is not None:
                prestamo = uow.prestamos.find_by_id(prestamo_id)
                if prestamo is None:
                    raise NoEncontrado("El préstamo no existe.")
                if prestamo.usuarioId.valor != usuario_id:
                    raise ErrorAplicacion("El préstamo no pertenece al usuario.", 422)
            try:
                sancion = Sancion.manual(
                    usuario_id=usuario_id, actor_id=actor.id.valor,
                    origen=origen, motivo=motivo, hoy=self.reloj.hoy(),
                    dias=dias, monto=self._monto(monto), prestamo_id=prestamo_id)
            except ErrorDominio as error:
                raise ErrorAplicacion(str(error), 422)
            guardada = uow.sanciones.save(sancion)
            uow.sanciones.actualizar_cache_usuario(usuario_id)
            vista = self._vista(guardada, {usuario_id: usuario.nombre})
            uow.commit()
        return vista

    def cerrar(self, sancion_id, resolucion):
        with self._uow() as uow:
            sancion = uow.sanciones.find_by_id(sancion_id)
            if sancion is None:
                raise NoEncontrado("La sanción no existe.")
            try:
                sancion.cerrar(resolucion, self.reloj.ahora())
            except ErrorDominio as error:
                raise Conflicto(str(error))
            guardada = uow.sanciones.save(sancion)
            uow.sanciones.actualizar_cache_usuario(sancion.usuarioId.valor)
            nombre = uow.usuarios.nombres_de([sancion.usuarioId.valor])
            vista = self._vista(guardada, nombre)
            uow.commit()
        return vista
