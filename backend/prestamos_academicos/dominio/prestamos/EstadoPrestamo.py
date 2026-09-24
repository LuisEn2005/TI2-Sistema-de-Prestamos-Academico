"""
<<valueobject>> EstadoPrestamo (enumeracion)
"""
from enum import Enum


class EstadoPrestamo(str, Enum):
    ACTIVO = "ACTIVO"
    DEVUELTO = "DEVUELTO"
    VENCIDO = "VENCIDO"
