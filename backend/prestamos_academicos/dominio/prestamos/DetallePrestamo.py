"""
<<entity>> DetallePrestamo
Generado a partir del bounded context: prestamos
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from ..shared_kernel import ItemId
from .CondicionDevolucion import CondicionDevolucion


@dataclass
class DetallePrestamo:
    id: Optional[int] = None
    itemId: Optional[ItemId] = None
    condicion: Optional[CondicionDevolucion] = None

