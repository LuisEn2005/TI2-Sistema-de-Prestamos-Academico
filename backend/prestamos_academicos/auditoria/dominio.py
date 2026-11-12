"""Historial unificado (RF17): un mismo movimiento para préstamos, reservas y sanciones.

No es una tabla nueva: cada movimiento se arma al vuelo desde los datos que ya
persisten los otros contextos (préstamos, eventos de reserva y sanciones)."""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional


class TipoEvento(str, Enum):
    PRESTAMO = "PRESTAMO"
    RESERVA = "RESERVA"
    SANCION = "SANCION"


@dataclass
class HistorialMovimiento:
    """Una entrada de la línea de tiempo consolidada, lista para serializar a JSON."""
    tipo: TipoEvento
    referencia_id: int
    fecha: date
    estado: str
    detalle: str
    usuario_id: int
    usuario: Optional[str] = None
    item_id: Optional[int] = None
    codigo: Optional[str] = None
    item: Optional[str] = None

    def a_json(self):
        return {
            "tipo": self.tipo.value,
            "referencia_id": self.referencia_id,
            "fecha": self.fecha.isoformat(),
            "estado": self.estado,
            "detalle": self.detalle,
            "usuario_id": self.usuario_id,
            "usuario": self.usuario,
            "item_id": self.item_id,
            "codigo": self.codigo,
            "item": self.item,
        }
