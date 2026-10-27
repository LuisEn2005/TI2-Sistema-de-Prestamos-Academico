"""Identificadores y roles compartidos por todo el dominio."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union
from uuid import UUID


@dataclass
class _Identificador:
    valor: Optional[Union[UUID, int]] = None


@dataclass
class ItemId(_Identificador):
    pass


@dataclass
class ModalidadId(_Identificador):
    pass


@dataclass
class PoliticaSancionId(_Identificador):
    pass


@dataclass
class PoliticaServicioId(_Identificador):
    pass


@dataclass
class PrestamoId(_Identificador):
    pass


@dataclass
class ReservaId(_Identificador):
    pass


@dataclass
class SancionId(_Identificador):
    pass


@dataclass
class UsuarioId(_Identificador):
    pass


class RolUsuario(str, Enum):
    ESTUDIANTE = "ESTUDIANTE"
    DOCENTE = "DOCENTE"
    ADMINISTRATIVO = "ADMINISTRATIVO"
    GESTOR_INVENTARIO = "GESTOR_INVENTARIO"
    ADMINISTRADOR_SISTEMA = "ADMINISTRADOR_SISTEMA"
