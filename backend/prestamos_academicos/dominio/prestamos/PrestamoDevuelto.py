"""
<<domain event>> PrestamoDevuelto
Generado a partir del bounded context: prestamos
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from ..shared_kernel import PrestamoId, ItemId
from .CondicionDevolucion import CondicionDevolucion


@dataclass
class PrestamoDevuelto:
    prestamoId: Optional[PrestamoId] = None
    itemId: Optional[ItemId] = None
    condicion: Optional[CondicionDevolucion] = None

