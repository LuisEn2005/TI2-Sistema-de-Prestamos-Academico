"""Diseño del dominio de reservas; su flujo se implementara en el Sprint 4."""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional

from ..compartido import ItemId, ReservaId, UsuarioId


class EstadoReserva(str, Enum):
    PENDIENTE = "PENDIENTE"
    CONFIRMADA = "CONFIRMADA"
    EXPIRADA = "EXPIRADA"
    CANCELADA = "CANCELADA"


@dataclass
class Reserva:
    id: Optional[ReservaId] = None
    usuarioId: Optional[UsuarioId] = None
    itemId: Optional[ItemId] = None
    fechaSolicitud: Optional[date] = None
    fechaReserva: Optional[date] = None
    estado: Optional[EstadoReserva] = None

    def confirmar(self):
        raise NotImplementedError("Planificado para el Sprint 4.")

    def expirar(self):
        raise NotImplementedError("Planificado para el Sprint 4.")

    def cancelar(self):
        raise NotImplementedError("Planificado para el Sprint 4.")


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
