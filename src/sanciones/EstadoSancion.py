"""
<<valueobject>> EstadoSancion (enumeracion)
"""
from enum import Enum


class EstadoSancion(str, Enum):
    ACTIVA = "ACTIVA"
    CERRADA = "CERRADA"
