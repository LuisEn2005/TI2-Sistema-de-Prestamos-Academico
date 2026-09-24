"""
<<valueobject>> TipoEvento (enumeracion)
"""
from enum import Enum


class TipoEvento(str, Enum):
    PRESTAMO = "PRESTAMO"
    RESERVA = "RESERVA"
    SANCION = "SANCION"
    ITEM = "ITEM"
