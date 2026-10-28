"""Dominio de reservas: solicitud, confirmación, cancelación y expiración."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import List, Optional, Tuple

from ..compartido import ErrorDominio, ItemId, ReservaId, RolUsuario, UsuarioId


class EstadoReserva(str, Enum):
    PENDIENTE = "PENDIENTE"
    CONFIRMADA = "CONFIRMADA"
    EXPIRADA = "EXPIRADA"
    CANCELADA = "CANCELADA"
    CONVERTIDA = "CONVERTIDA"


ESTADOS_ACTIVOS = (EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA)


@dataclass
class Reserva:
    id: Optional[ReservaId] = None
    usuarioId: Optional[UsuarioId] = None
    itemId: Optional[ItemId] = None
    rolSolicitante: Optional[RolUsuario] = None
    fechaSolicitud: Optional[datetime] = None
    fechaReserva: Optional[date] = None
    fechaExpiracion: Optional[date] = None
    estado: EstadoReserva = EstadoReserva.PENDIENTE
    eventos: List[object] = field(default_factory=list, repr=False, compare=False)

    @classmethod
    def solicitar(cls, *, usuario_id: UsuarioId, item_id: ItemId, rol: RolUsuario,
                  fecha_solicitud: datetime, fecha_reserva: date,
                  dias_gracia: int, hoy: date) -> "Reserva":
        if fecha_reserva < hoy:
            raise ErrorDominio("La fecha de reserva no puede estar en el pasado.")
        if dias_gracia < 0:
            raise ErrorDominio("Los días de gracia de la reserva no pueden ser negativos.")
        return cls(
            usuarioId=usuario_id,
            itemId=item_id,
            rolSolicitante=rol,
            fechaSolicitud=fecha_solicitud,
            fechaReserva=fecha_reserva,
            fechaExpiracion=fecha_reserva + timedelta(days=dias_gracia),
            estado=EstadoReserva.PENDIENTE,
        )

    def confirmar(self) -> None:
        if self.estado != EstadoReserva.PENDIENTE:
            raise ErrorDominio("Solo una reserva pendiente puede confirmarse.")
        self.estado = EstadoReserva.CONFIRMADA
        self.eventos.append(ReservaConfirmada(self.id, self.usuarioId, self.itemId))

    def expirar(self) -> None:
        if self.estado not in ESTADOS_ACTIVOS:
            raise ErrorDominio("La reserva ya no está activa.")
        self.estado = EstadoReserva.EXPIRADA
        self.eventos.append(ReservaExpirada(self.id, self.itemId))

    def cancelar(self) -> None:
        if self.estado not in ESTADOS_ACTIVOS:
            raise ErrorDominio("La reserva ya no puede cancelarse.")
        self.estado = EstadoReserva.CANCELADA
        self.eventos.append(ReservaCancelada(self.id, self.itemId))

    def convertir(self) -> None:
        if self.estado != EstadoReserva.CONFIRMADA:
            raise ErrorDominio("Solo una reserva confirmada puede convertirse en préstamo.")
        self.estado = EstadoReserva.CONVERTIDA

    def estaVencida(self, hoy: date) -> bool:
        return self.estado in ESTADOS_ACTIVOS and bool(
            self.fechaExpiracion and hoy > self.fechaExpiracion)


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
               pagina: int = 1, limite: int = 20) -> Tuple[List[Reserva], int]: ...

    @abstractmethod
    def find_vencidas(self, hoy: date) -> List[Reserva]: ...

    @abstractmethod
    def find_activa_por_item(self, item_id: int) -> Optional[Reserva]: ...

    @abstractmethod
    def contar_activas_usuario(self, usuario_id: int) -> int: ...
