"""Dominio de reservas: solicitud, confirmación, cancelación y expiración."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import List, Optional, Tuple

from ..compartido import (
    ErrorDominio, ItemId, ModalidadId, ReservaId, RolUsuario, UsuarioId,
)


class EstadoReserva(str, Enum):
    PENDIENTE = "PENDIENTE"
    CONFIRMADA = "CONFIRMADA"
    EXPIRADA = "EXPIRADA"
    CANCELADA = "CANCELADA"
    CONVERTIDA = "CONVERTIDA"
    RECHAZADA = "RECHAZADA"
    RETIRADA = "RETIRADA"


ESTADOS_ACTIVOS = (EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA)


@dataclass
class Reserva:
    id: Optional[ReservaId] = None
    usuarioId: Optional[UsuarioId] = None
    itemId: Optional[ItemId] = None
    rolSolicitante: Optional[RolUsuario] = None
    modalidadId: Optional[ModalidadId] = None
    fechaSolicitud: Optional[datetime] = None
    fechaInicio: Optional[date] = None
    fechaFin: Optional[date] = None
    estado: EstadoReserva = EstadoReserva.PENDIENTE
    confirmadaPorUsuarioId: Optional[UsuarioId] = None
    confirmadaEn: Optional[datetime] = None
    motivoResolucion: Optional[str] = None
    eventos: List[object] = field(default_factory=list, repr=False, compare=False)

    @classmethod
    def solicitar(cls, *, usuario_id: UsuarioId, item_id: ItemId, rol: RolUsuario,
                  modalidad_id: Optional[ModalidadId], fecha_solicitud: datetime,
                  fecha_inicio: date, fecha_fin: date, hoy: date) -> "Reserva":
        if fecha_inicio < hoy:
            raise ErrorDominio("La fecha inicial no puede estar en el pasado.")
        if fecha_fin < fecha_inicio:
            raise ErrorDominio("La fecha final no puede ser anterior a la inicial.")
        return cls(
            usuarioId=usuario_id,
            itemId=item_id,
            rolSolicitante=rol,
            modalidadId=modalidad_id,
            fechaSolicitud=fecha_solicitud,
            fechaInicio=fecha_inicio,
            fechaFin=fecha_fin,
            estado=EstadoReserva.PENDIENTE,
        )

    def confirmar(self, actor_id: UsuarioId, ahora: datetime, fecha_fin=None) -> None:
        if self.estado != EstadoReserva.PENDIENTE:
            raise ErrorDominio("Solo una reserva pendiente puede confirmarse.")
        if fecha_fin is not None:
            if fecha_fin < self.fechaInicio or fecha_fin > self.fechaFin:
                raise ErrorDominio("La confirmación solo puede mantener o acortar el rango.")
            self.fechaFin = fecha_fin
        self.estado = EstadoReserva.CONFIRMADA
        self.confirmadaPorUsuarioId = actor_id
        self.confirmadaEn = ahora
        self.eventos.append(ReservaConfirmada(self.id, self.usuarioId, self.itemId))

    def expirar(self) -> None:
        if self.estado not in ESTADOS_ACTIVOS:
            raise ErrorDominio("La reserva ya no está activa.")
        self.estado = EstadoReserva.EXPIRADA
        self.eventos.append(ReservaExpirada(self.id, self.itemId))

    def retirar(self, motivo: Optional[str] = None) -> None:
        if self.estado != EstadoReserva.PENDIENTE:
            raise ErrorDominio("Solo una solicitud pendiente puede retirarse.")
        self.estado = EstadoReserva.RETIRADA
        self.motivoResolucion = (motivo or "Solicitud retirada por el titular.").strip()

    def cancelar(self, motivo: Optional[str] = None) -> None:
        if self.estado != EstadoReserva.CONFIRMADA:
            raise ErrorDominio("Solo una reserva confirmada puede cancelarse.")
        self.estado = EstadoReserva.CANCELADA
        self.motivoResolucion = (motivo or "Reserva cancelada por el titular.").strip()
        self.eventos.append(ReservaCancelada(self.id, self.itemId))

    def rechazar(self, motivo: str) -> None:
        if self.estado != EstadoReserva.PENDIENTE:
            raise ErrorDominio("Solo una reserva pendiente puede rechazarse.")
        self.estado = EstadoReserva.RECHAZADA
        self.motivoResolucion = (motivo or "Solicitud incompatible con otra reserva.").strip()

    def convertir(self) -> None:
        if self.estado != EstadoReserva.CONFIRMADA:
            raise ErrorDominio("Solo una reserva confirmada puede convertirse en préstamo.")
        self.estado = EstadoReserva.CONVERTIDA

    def estaVencida(self, hoy: date) -> bool:
        return self.estado in ESTADOS_ACTIVOS and bool(
            self.fechaInicio and hoy > self.fechaInicio)

    def seSolapa(self, inicio: date, fin: date) -> bool:
        return bool(self.fechaInicio and self.fechaFin
                    and self.fechaInicio <= fin and inicio <= self.fechaFin)


@dataclass
class ReservaConfirmada:
    reservaId: Optional[ReservaId] = None
    usuarioId: Optional[UsuarioId] = None
    itemId: Optional[ItemId] = None


@dataclass
class ReservaExpirada:
    reservaId: Optional[ReservaId] = None
    itemId: Optional[ItemId] = None


@dataclass
class ReservaCancelada:
    reservaId: Optional[ReservaId] = None
    itemId: Optional[ItemId] = None


class IReservaRepository(ABC):
    @abstractmethod
    def save(self, reserva: Reserva) -> Reserva: ...

    @abstractmethod
    def find_by_id(self, reserva_id: int) -> Optional[Reserva]: ...

    @abstractmethod
    def buscar(self, *, usuario_id: Optional[int] = None,
               estado: Optional[EstadoReserva] = None,
               solo_activas: bool = False,
               pagina: int = 1, limite: int = 20) -> Tuple[List[Reserva], int]: ...

    @abstractmethod
    def find_vencidas(self, hoy: date) -> List[Reserva]: ...

    @abstractmethod
    def find_activa_por_item(self, item_id: int) -> Optional[Reserva]: ...

    @abstractmethod
    def find_activas_por_item(self, item_id: int) -> List[Reserva]: ...

    @abstractmethod
    def find_confirmadas_solapadas(
            self, item_id: int, inicio: date, fin: date,
            excluir_id: Optional[int] = None) -> List[Reserva]: ...

    @abstractmethod
    def find_pendientes_solapadas(
            self, item_id: int, inicio: date, fin: date,
            excluir_id: Optional[int] = None) -> List[Reserva]: ...

    @abstractmethod
    def find_usuario_item_solapadas(
            self, usuario_id: int, item_id: int, inicio: date, fin: date) -> List[Reserva]: ...

    @abstractmethod
    def listar_activas(self) -> List[Reserva]: ...

    @abstractmethod
    def contar_activas_usuario(self, usuario_id: int) -> int: ...

    @abstractmethod
    def registrar_evento(self, reserva_id: int, tipo: str, ahora: datetime, **datos): ...

    @abstractmethod
    def listar_eventos(self, reserva_id: int): ...
