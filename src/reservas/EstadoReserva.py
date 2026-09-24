"""
<<valueobject>> EstadoReserva (enumeracion)
"""
from enum import Enum


class EstadoReserva(str, Enum):
    PENDIENTE = "PENDIENTE"
    CONFIRMADA = "CONFIRMADA"
    EXPIRADA = "EXPIRADA"
    CANCELADA = "CANCELADA"
