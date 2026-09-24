"""
<<domain event>> ReservaCancelada
Generado a partir del bounded context: reservas
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from ..shared_kernel import ReservaId, ItemId


@dataclass
class ReservaCancelada:
    reservaId: Optional[ReservaId] = None
    itemId: Optional[ItemId] = None

