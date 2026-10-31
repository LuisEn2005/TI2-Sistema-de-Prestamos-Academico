"""Solicitudes de reserva por rango y selección manual del gestor."""

from datetime import timedelta
from typing import Optional

from .dominio import EstadoReserva, Reserva
from ..calendario_laboral.servicio import CalendarioLaboralApplicationService
from ..compartido import ErrorDominio, ItemId, ModalidadId, RolUsuario, UsuarioId
from ..compartido import Conflicto, ErrorAplicacion, NoEncontrado, SinPermiso
from ..compartido.reloj import Reloj
from ..configuracion_servicio.servicio import MODALIDAD_IN_SITU
from ..identidad import Permiso
from ..inventario import EstadoItem


MAX_DIAS_ANTICIPACION = 365


class ReservaApplicationService:
    def __init__(self, fabrica_uow, identidad, reloj: Optional[Reloj] = None):
        self._uow = fabrica_uow
        self._identidad = identidad
        self.reloj = reloj or Reloj()
        self.calendario = CalendarioLaboralApplicationService(fabrica_uow, self.reloj)

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
            reserva.expirar()
            uow.reservas.save(reserva)
        return len(vencidas)

    def expirar_vencidas(self):
        with self._uow() as uow:
            cantidad = self._expirar_en_uow(uow)
            uow.commit()
        return cantidad

    def _vista(self, reserva, nombres, items, modalidades):
        item = items.get(reserva.itemId.valor)
        return {
            "id": reserva.id.valor,
            "usuario_id": reserva.usuarioId.valor,
            "usuario": nombres.get(reserva.usuarioId.valor),
            "item_id": reserva.itemId.valor,
            "codigo": item.codigo if item else None,
            "item": item.nombre if item else None,
            "rol_solicitante": reserva.rolSolicitante.value,
            "modalidad_id": reserva.modalidadId.valor if reserva.modalidadId else None,
            "modalidad": modalidades.get(
                reserva.modalidadId.valor) if reserva.modalidadId else None,
            "fecha_solicitud": reserva.fechaSolicitud.isoformat(),
            "fecha_inicio": reserva.fechaInicio.isoformat(),
            "fecha_fin": reserva.fechaFin.isoformat(),
            "fecha_reserva": reserva.fechaInicio.isoformat(),
            "estado": reserva.estado.value,
            "motivo_resolucion": reserva.motivoResolucion,
        }

    def _vistas(self, uow, reservas):
        nombres = uow.usuarios.nombres_de([r.usuarioId.valor for r in reservas])
        items = uow.items.find_by_ids([r.itemId.valor for r in reservas])
        modalidades = {m.id.valor: m.nombre for m in uow.modalidades.listar()}
        return [self._vista(r, nombres, items, modalidades) for r in reservas]

    def listar(self, actor, *, estado=None, pagina=1, limite=20):
        with self._uow() as uow:
            self._expirar_en_uow(uow)
            reservas, total = uow.reservas.buscar(
                usuario_id=None if self._ve_todo(actor) else actor.id.valor,
                estado=estado, pagina=pagina, limite=limite)
            vistas = self._vistas(uow, reservas)
            uow.commit()
        return {"reservas": vistas, "total": total, "pagina": pagina, "limite": limite}

    def _politica(self, uow, rol, modalidad_id, item):
        if modalidad_id is None:
            politicas = [p for p in uow.politicas.listar_por_rol(rol)
                         if p.permiteTipo(item.TIPO)]
            if not politicas:
                raise ErrorAplicacion(
                    f"La política del perfil {rol.value} no permite reservar {item.codigo}.", 422)
            return min(politicas, key=lambda p: p.maxItemsSimultaneos)
        modalidad = uow.modalidades.find_by_id(modalidad_id)
        if modalidad is None:
            raise NoEncontrado("La modalidad no existe.")
        if not modalidad.activo:
            raise ErrorAplicacion(f"La modalidad «{modalidad.nombre}» no está activa.", 422)
        politica = uow.politicas.find_by_rol_y_modalidad(rol, modalidad_id)
        if politica is None or not politica.permiteTipo(item.TIPO):
            raise ErrorAplicacion(
                f"La política del perfil {rol.value} no permite reservar {item.codigo} "
                "bajo esa modalidad.", 422)
        return politica

    def _validar_rango(self, uow, politica, inicio, fin):
        self.calendario.validar_laborable(uow, inicio, "fecha de inicio")
        self.calendario.validar_laborable(uow, fin, "fecha de devolución")
        modalidad = uow.modalidades.find_by_id(politica.modalidadId.valor)
        if modalidad.nombre == MODALIDAD_IN_SITU:
            if fin != inicio:
                raise ErrorAplicacion("Una reserva in situ empieza y termina el mismo día.", 422)
            return 1
        dias = (fin - inicio).days
        if dias < 1 or dias > politica.diasPrestamo:
            raise ErrorAplicacion(
                f"El rango externo debe estar entre 1 y {politica.diasPrestamo} días.", 422)
        return dias

    def crear(self, actor, item_id, inicio, fin, modalidad_id=None, rol_solicitante=None):
        hoy = self.reloj.hoy()
        if inicio > hoy + timedelta(days=MAX_DIAS_ANTICIPACION):
            raise ErrorAplicacion(
                f"La reserva puede solicitarse con hasta {MAX_DIAS_ANTICIPACION} días "
                "de anticipación.", 422)
        self.expirar_vencidas()
        with self._uow() as uow:
            uow.sanciones.sincronizar_vencidas(hoy, self.reloj.ahora(), actor.id.valor)
            usuario = uow.usuarios.find_by_id(actor.id.valor)
            motivo = usuario.motivoNoHabilitado()
            if motivo:
                raise ErrorAplicacion(motivo, 422)
            rol = self._elegir_rol(usuario, rol_solicitante)
            item = uow.items.find_by_id(item_id)
            if item is None:
                raise NoEncontrado("El recurso no existe.")
            if item.estado not in (EstadoItem.DISPONIBLE, EstadoItem.PRESTADO):
                raise Conflicto(
                    f"El recurso {item.codigo} está {item.estado.value} y no puede reservarse.")
            politica = self._politica(uow, rol, modalidad_id, item)
            if modalidad_id is not None:
                self._validar_rango(uow, politica, inicio, fin)

            uow.usuarios.bloquear(usuario.id.valor)
            prestamos = uow.prestamos.contar_items_activos(usuario.id.valor)
            reservas = uow.reservas.contar_activas_usuario(usuario.id.valor)
            if prestamos + reservas >= politica.maxItemsSimultaneos:
                raise ErrorAplicacion(
                    f"Alcanzó el cupo compartido de {politica.maxItemsSimultaneos} recursos "
                    f"({prestamos} prestados y {reservas} reservados).", 422)
            try:
                reserva = Reserva.solicitar(
                    usuario_id=UsuarioId(usuario.id.valor), item_id=ItemId(item_id), rol=rol,
                    modalidad_id=ModalidadId(modalidad_id) if modalidad_id else None,
                    fecha_solicitud=self.reloj.ahora(), fecha_inicio=inicio,
                    fecha_fin=fin, hoy=hoy)
            except ErrorDominio as error:
                raise ErrorAplicacion(str(error), 422)
            guardada = uow.reservas.save(reserva)
            vista = self._vistas(uow, [guardada])[0]
            uow.commit()
        return vista

    def confirmar(self, actor, reserva_id, fecha_fin=None):
        self.expirar_vencidas()
        with self._uow() as uow:
            reserva = uow.reservas.find_by_id(reserva_id)
            if reserva is None:
                raise NoEncontrado("La reserva no existe.")
            uow.items.bloquear(reserva.itemId.valor)
            item = uow.items.find_by_id(reserva.itemId.valor)
            if item.estado not in (EstadoItem.DISPONIBLE, EstadoItem.PRESTADO):
                raise Conflicto(f"El recurso está {item.estado.value}.")
            fin = fecha_fin or reserva.fechaFin
            politica = self._politica(
                uow, reserva.rolSolicitante,
                reserva.modalidadId.valor if reserva.modalidadId else None, item)
            if reserva.modalidadId:
                self._validar_rango(uow, politica, reserva.fechaInicio, fin)
            uow.usuarios.bloquear(reserva.usuarioId.valor)
            prestamos = uow.prestamos.contar_items_activos(reserva.usuarioId.valor)
            reservas = uow.reservas.contar_activas_usuario(reserva.usuarioId.valor)
            if prestamos + reservas > politica.maxItemsSimultaneos:
                raise ErrorAplicacion(
                    f"El usuario supera el cupo compartido de "
                    f"{politica.maxItemsSimultaneos} recursos.", 422)
            ocupado = self.calendario.rango_ocupado(
                uow, reserva.itemId.valor, reserva.fechaInicio, fin, reserva.id.valor)
            if ocupado is not None:
                raise Conflicto(
                    f"El recurso no está libre durante todo el rango; está ocupado hasta "
                    f"{ocupado.isoformat()}.")
            try:
                reserva.confirmar(
                    UsuarioId(actor.id.valor), self.reloj.ahora(), fecha_fin=fecha_fin)
            except ErrorDominio as error:
                raise Conflicto(str(error))
            guardada = uow.reservas.save(reserva)
            for pendiente in uow.reservas.find_pendientes_solapadas(
                    reserva.itemId.valor, reserva.fechaInicio, reserva.fechaFin,
                    excluir_id=reserva.id.valor):
                pendiente.rechazar("Otra solicitud fue confirmada para este rango.")
                uow.reservas.save(pendiente)
            vista = self._vistas(uow, [guardada])[0]
            uow.commit()
        return vista

    def rechazar(self, reserva_id, motivo):
        with self._uow() as uow:
            reserva = uow.reservas.find_by_id(reserva_id)
            if reserva is None:
                raise NoEncontrado("La reserva no existe.")
            try:
                reserva.rechazar(motivo)
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
            try:
                reserva.cancelar()
            except ErrorDominio as error:
                raise Conflicto(str(error))
            guardada = uow.reservas.save(reserva)
            vista = self._vistas(uow, [guardada])[0]
            uow.commit()
        return vista
