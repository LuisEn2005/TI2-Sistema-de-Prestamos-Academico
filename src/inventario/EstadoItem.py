"""
<<valueobject>> EstadoItem (enumeracion)
"""
from enum import Enum


class EstadoItem(str, Enum):
    DISPONIBLE = "DISPONIBLE"
    PRESTADO = "PRESTADO"
    RESERVADO = "RESERVADO"
    EN_MANTENIMIENTO = "EN_MANTENIMIENTO"
    DADO_DE_BAJA = "DADO_DE_BAJA"
    EXTRAVIADO = "EXTRAVIADO"
