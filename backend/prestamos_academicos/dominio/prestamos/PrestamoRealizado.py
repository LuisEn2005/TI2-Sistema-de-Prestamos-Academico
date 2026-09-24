"""
<<domain event>> PrestamoRealizado
Generado a partir del bounded context: prestamos
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date, datetime
from ..shared_kernel import PrestamoId, ItemId


@dataclass
class PrestamoRealizado:
    prestamoId: Optional[PrestamoId] = None
    itemId: Optional[ItemId] = None
    fecha: Optional[datetime] = None

