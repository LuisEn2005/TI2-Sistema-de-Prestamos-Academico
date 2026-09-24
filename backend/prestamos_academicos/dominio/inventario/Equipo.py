"""
<<entity>> Equipo
Generado a partir del bounded context: inventario
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from .Item import Item


@dataclass
class Equipo(Item):
    numeroSerie: Optional[str] = None
    marcaModelo: Optional[str] = None

