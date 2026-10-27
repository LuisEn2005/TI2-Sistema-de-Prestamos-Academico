"""Diseño del historial auditable; su persistencia llegara en el Sprint 6."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from ..compartido import UsuarioId


class TipoEvento(str, Enum):
    PRESTAMO = "PRESTAMO"
    RESERVA = "RESERVA"
    SANCION = "SANCION"
    ITEM = "ITEM"


@dataclass
class HistorialMovimiento:
    id: Optional[int] = None
    tipoEvento: Optional[TipoEvento] = None
    fechaEvento: Optional[datetime] = None
    detalle: Optional[str] = None
    entidadOrigenId: Optional[str] = None
    usuarioResponsableId: Optional[UsuarioId] = None
