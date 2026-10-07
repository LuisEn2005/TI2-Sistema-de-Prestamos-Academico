"""
<<valueobject>> RolUsuario (enumeracion)
"""
from enum import Enum


class RolUsuario(str, Enum):
    ESTUDIANTE = "ESTUDIANTE"
    DOCENTE = "DOCENTE"
    ADMINISTRATIVO = "ADMINISTRATIVO"
    GESTOR_INVENTARIO = "GESTOR_INVENTARIO"
    ADMINISTRADOR_SISTEMA = "ADMINISTRADOR_SISTEMA"
