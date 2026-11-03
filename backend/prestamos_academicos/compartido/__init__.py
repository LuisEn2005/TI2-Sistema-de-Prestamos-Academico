"""Piezas transversales usadas por los modulos funcionales."""

from .dominio import (
    EspacioTrabajo, ItemId, ModalidadId, PoliticaSancionId, PoliticaServicioId, PrestamoId,
    ReservaId, RolUsuario, SancionId, UsuarioId,
)
from .errores import (
    Conflicto, ErrorAplicacion, ErrorDominio, NoAutenticado, NoEncontrado,
    SinPermiso, TransicionInvalida,
)

__all__ = [
    "Conflicto", "ErrorAplicacion", "ErrorDominio", "EspacioTrabajo", "ItemId", "ModalidadId",
    "NoAutenticado", "NoEncontrado",
    "PoliticaSancionId", "PoliticaServicioId", "PrestamoId", "ReservaId",
    "RolUsuario", "SancionId", "SinPermiso", "TransicionInvalida", "UsuarioId",
]
