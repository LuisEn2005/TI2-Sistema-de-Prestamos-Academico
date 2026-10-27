"""Diseño del dominio de sanciones; su flujo se implementara en el Sprint 5."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from ..compartido import PrestamoId, SancionId, UsuarioId


class EstadoSancion(str, Enum):
    ACTIVA = "ACTIVA"
    CERRADA = "CERRADA"


class OrigenSancion(str, Enum):
    RETRASO = "RETRASO"
    DANO = "DANO"
    PERDIDA = "PERDIDA"


@dataclass
class Monto:
    cantidad: Optional[Decimal] = None
    moneda: Optional[str] = None


@dataclass
class Sancion:
    id: Optional[SancionId] = None
    usuarioId: Optional[UsuarioId] = None
    prestamoId: Optional[PrestamoId] = None
    origen: Optional[OrigenSancion] = None
    motivo: Optional[str] = None
    monto: Optional[Monto] = None
    fechaInicio: Optional[date] = None
    fechaFin: Optional[date] = None
    estado: Optional[EstadoSancion] = None

    def levantar(self):
        raise NotImplementedError("Planificado para el Sprint 5.")


@dataclass
class SancionGenerada:
    sancionId: Optional[SancionId] = None
    usuarioId: Optional[UsuarioId] = None


@dataclass
class SancionCerrada:
    sancionId: Optional[SancionId] = None
    usuarioId: Optional[UsuarioId] = None
