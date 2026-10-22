"""
<<entity>> DetallePrestamo
Un ítem incluido en el préstamo y la condición en que volvió.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from ..shared_kernel import ItemId
from .CondicionDevolucion import CondicionDevolucion


@dataclass
class DetallePrestamo:
    id: Optional[int] = None
    itemId: Optional[ItemId] = None
    condicion: Optional[CondicionDevolucion] = None
    observacion: Optional[str] = None
