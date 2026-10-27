"""Politicas y modalidades configurables del servicio."""

from .dominio import (
    IModalidadRepository, IPoliticaRepository, Modalidad, PoliticaSancion,
    PoliticaServicio,
)

__all__ = [
    "IModalidadRepository", "IPoliticaRepository", "Modalidad",
    "PoliticaSancion", "PoliticaServicio",
]
