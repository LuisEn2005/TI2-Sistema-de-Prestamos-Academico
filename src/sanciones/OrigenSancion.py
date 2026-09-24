"""
<<valueobject>> OrigenSancion (enumeracion)
"""
from enum import Enum


class OrigenSancion(str, Enum):
    RETRASO = "RETRASO"
    DANO = "DANO"
    PERDIDA = "PERDIDA"
