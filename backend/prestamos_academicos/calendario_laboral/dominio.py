"""Reglas mínimas del calendario laboral institucional."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional


class TipoCierre(str, Enum):
    FERIADO = "FERIADO"
    HUELGA = "HUELGA"
    OTRO = "OTRO"


@dataclass
class DiaNoLaborable:
    id: Optional[int] = None
    fechaInicio: Optional[date] = None
    fechaFin: Optional[date] = None
    tipo: TipoCierre = TipoCierre.OTRO
    motivo: str = ""
    activo: bool = True
    creadoPorUsuarioId: Optional[int] = None
    creadoEn: Optional[datetime] = None

    def contiene(self, fecha: date) -> bool:
        return bool(self.activo and self.fechaInicio <= fecha <= self.fechaFin)
