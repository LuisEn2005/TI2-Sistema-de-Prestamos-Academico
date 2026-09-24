"""
<<entity>> Libro
Generado a partir del bounded context: inventario
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from .Item import Item


@dataclass
class Libro(Item):
    isbn: Optional[str] = None
    autor: Optional[str] = None
    editorial: Optional[str] = None

