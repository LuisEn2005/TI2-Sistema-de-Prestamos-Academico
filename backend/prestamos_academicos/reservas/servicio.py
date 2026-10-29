"""Casos de uso de reservas (Sprint 4: RF07–RF09)."""

from datetime import timedelta
from typing import Optional

from sqlalchemy.exc import IntegrityError

from .dominio import EstadoReserva, Reserva
from ..compartido import ErrorDominio, ItemId, RolUsuario, UsuarioId
from ..compartido import Conflicto, ErrorAplicacion, NoEncontrado, SinPermiso
from ..compartido.reloj import Reloj
from ..identidad import Permiso
from ..inventario import EstadoItem


MAX_DIAS_ANTICIPACION = 365


class ReservaApplicationService:
    def __init__(self, fabrica_uow, identidad, reloj: Optional[Reloj] = None):
        self._uow = fabrica_uow
        self._identidad = identidad
        self.reloj = reloj or Reloj()

    def _ve_todo(self, actor):
        return Permiso.CONFIRMAR_RESERVA in self._identidad.permisos_de(actor)

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
                    f"El usuario no tiene el perfil {rol.value} para reservar.", 422)
        elif len(posibles) == 1:
            rol = posibles[0]
        else:
            raise ErrorAplicacion(
                "El usuario tiene varios perfiles: indique con cuál reserva.", 400)
        if not usuario.vinculacionVigentePara(rol):
            raise ErrorAplicacion(
                f"El usuario no tiene vinculación vigente como {rol.value}.", 422)
        return rol

    def _expirar_en_uow(self, uow):
        vencidas = uow.reservas.find_vencidas(self.reloj.hoy())
        for reserva in vencidas:
            item = uow.items.find_by_id(reserva.itemId.valor)
            if item and item.estado == EstadoItem.RESERVADO:
                if not uow.items.cambiar_estado_si(
                        item.id.valor, EstadoItem.RESERVADO, EstadoItem.DISPONIBLE):
                    raise Conflicto(
                        f"No se pudo liberar el recurso {item.codigo} al expirar la reserva.")
            reserva.expirar()
            uow.reservas.save(reserva)
        return len(vencidas)

    def expirar_vencidas(self):
        with self._uow() as uow:
            cantidad = self._expirar_en_uow(uow)
            uow.commit()
        return cantidad

    def _vista(self, reserva, nombres, items):
        item = items.get(reserva.itemId.valor)
        return {
            "id": reserva.id.valor,
            "usuario_id": reserva.usuarioId.valor,
            "usuario": nombres.get(reserva.usuarioId.valor),
            "item_id": reserva.itemId.valor,
            "codigo": item.codigo if item else None,
            "item": item.nombre if item else None,
            "rol_solicitante": reserva.rolSolicitante.value,
            "fecha_solicitud": reserva.fechaSolicitud.isoformat(),
            "fecha_reserva": reserva.fechaReserva.isoformat(),
            "estado": reserva.estado.value,
        }

    def _vistas(self, uow, reservas):
        nombres = uow.usuarios.nombres_de([r.usuarioId.valor for r in reservas])
        items = uow.items.find_by_ids([r.itemId.valor for r in reservas])
        return [self._vista(r, nombres, items) for r in reservas]

    def listar(self, actor, *, estado=None, pagina=1, limite=20):
        with self._uow() as uow:
            self._expirar_en_uow(uow)
            reservas, total = uow.reservas.buscar(
                usuario_id=None if self._ve_todo(actor) else actor.id.valor,
                estado=estado, pagina=pagina, limite=limite)
            vistas = self._vistas(uow, reservas)
            uow.commit()
        return {"reservas": vistas, "total": total, "pagina": pagina, "limite": limite}

    def crear(self, actor, item_id, fecha_reserva, rol_solicitante=None):
        hoy = self.reloj.hoy()
        if fecha_reserva > hoy + timedelta(days=MAX_DIAS_ANTICIPACION):
            raise ErrorAplicacion(
                f"La reserva puede solicitarse con hasta {MAX_DIAS_ANTICIPACION} días de anticipación.",
                422)
        self.expirar_vencidas()
        with self._uow() as uow:
            uow.sanciones.sincronizar_vencidas(
                hoy, self.reloj.ahora(), actor.id.valor)
            usuario = uow.usuarios.find_by_id(actor.id.valor)
            motivo = usuario.motivoNoHabilitado()
            if motivo:
                raise ErrorAplicacion(motivo, 422)
            rol = self._elegir_rol(usuario, rol_solicitante)
            politicas = uow.politicas.listar_por_rol(rol)
            if not politicas:
                raise ErrorAplicacion("El perfil no tiene políticas de servicio.", 422)
            item = uow.items.find_by_id(item_id)
            if item is None:
                raise NoEncontrado("El recurso no existe.")
            if uow.reservas.find_activa_por_item(item_id):
                raise Conflicto("El recurso ya tiene una reserva activa.")
            if item.estado not in (EstadoItem.DISPONIBLE, EstadoItem.PRESTADO):
                raise Conflicto(
                    f"El recurso {item.codigo} está {item.estado.value} y no puede reservarse.")
            aplicables = [p for p in politicas if p.permiteTipo(item.TIPO)]
            if not aplicables:
                raise ErrorAplicacion(
                    f"La política del perfil {rol.value} no permite reservar {item.codigo}.", 422)
            # La modalidad se elige al convertir la reserva. Hasta entonces se
            # aplica el límite más restrictivo de las políticas compatibles.
            max_reservas = min(p.maxItemsSimultaneos for p in aplicables)
            if uow.reservas.contar_activas_usuario(usuario.id.valor) >= max_reservas:
                raise ErrorAplicacion(
                    f"Alcanzó el máximo de {max_reservas} reservas activas.", 422)
            try:
                reserva = Reserva.solicitar(
                    usuario_id=UsuarioId(usuario.id.valor), item_id=ItemId(item_id), rol=rol,
                    fecha_solicitud=self.reloj.ahora(), fecha_reserva=fecha_reserva, hoy=hoy)
            except ErrorDominio as error:
                raise ErrorAplicacion(str(error), 422)
            if item.estado == EstadoItem.DISPONIBLE and not uow.items.cambiar_estado_si(
                    item_id, EstadoItem.DISPONIBLE, EstadoItem.RESERVADO):
                raise Conflicto("El recurso dejó de estar disponible.")
            try:
                guardada = uow.reservas.save(reserva)
                vista = self._vistas(uow, [guardada])[0]
                uow.commit()
            except IntegrityError:
                raise Conflicto("El recurso ya tiene una reserva activa.")
        return vista

    def confirmar(self, reserva_id):
        self.expirar_vencidas()
        with self._uow() as uow:
            reserva = uow.reservas.find_by_id(reserva_id)
            if reserva is None:
                raise NoEncontrado("La reserva no existe.")
            item = uow.items.find_by_id(reserva.itemId.valor)
            if item.estado == EstadoItem.PRESTADO:
                raise Conflicto("El recurso sigue prestado; confirme la reserva después de su devolución.")
            if item.estado == EstadoItem.DISPONIBLE and not uow.items.cambiar_estado_si(
                    item.id.valor, EstadoItem.DISPONIBLE, EstadoItem.RESERVADO):
                raise Conflicto("El recurso dejó de estar disponible.")
            if item.estado not in (EstadoItem.DISPONIBLE, EstadoItem.RESERVADO):
                raise Conflicto(f"El recurso está {item.estado.value}.")
            try:
                reserva.confirmar()
            except ErrorDominio as error:
                raise Conflicto(str(error))
            guardada = uow.reservas.save(reserva)
            vista = self._vistas(uow, [guardada])[0]
            uow.commit()
        return vista

    def cancelar(self, actor, reserva_id):
        self.expirar_vencidas()
        with self._uow() as uow:
            reserva = uow.reservas.find_by_id(reserva_id)
            if reserva is None:
                raise NoEncontrado("La reserva no existe.")
            if reserva.usuarioId.valor != actor.id.valor and not self._ve_todo(actor):
                raise SinPermiso("Solo el titular o un gestor puede cancelar la reserva.")
            item = uow.items.find_by_id(reserva.itemId.valor)
            try:
                reserva.cancelar()
            except ErrorDominio as error:
                raise Conflicto(str(error))
            if item and item.estado == EstadoItem.RESERVADO and not uow.items.cambiar_estado_si(
                    item.id.valor, EstadoItem.RESERVADO, EstadoItem.DISPONIBLE):
                raise Conflicto("El recurso cambió de estado mientras se cancelaba la reserva.")
            guardada = uow.reservas.save(reserva)
            vista = self._vistas(uow, [guardada])[0]
            uow.commit()
        return vista
