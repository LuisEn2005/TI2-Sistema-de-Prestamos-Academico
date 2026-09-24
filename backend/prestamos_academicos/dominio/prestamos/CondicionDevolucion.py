"""
<<valueobject>> CondicionDevolucion (enumeracion)
"""
from enum import Enum


class CondicionDevolucion(str, Enum):
    BUEN_ESTADO = "BUEN_ESTADO"
    DANADO = "DANADO"
    PERDIDO = "PERDIDO"
