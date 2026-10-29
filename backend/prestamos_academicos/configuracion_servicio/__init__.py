"""Politicas y modalidades configurables del servicio."""

from .dominio import (
    IModalidadRepository, IPoliticaRepository, Modalidad, PoliticaServicio,
)

__all__ = [
    "IModalidadRepository", "IPoliticaRepository", "Modalidad",
    "PoliticaServicio",
]
