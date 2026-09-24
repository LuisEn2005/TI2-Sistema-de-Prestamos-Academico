"""
<<entity>> Mobiliario
Generado a partir del bounded context: inventario
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from .Item import Item


@dataclass
class Mobiliario(Item):
    tipoMobiliario: Optional[str] = None
    ubicacionHabitual: Optional[str] = None

