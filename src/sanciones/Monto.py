"""
<<valueobject>> Monto
Generado a partir del bounded context: sanciones
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from decimal import Decimal


@dataclass
class Monto:
    cantidad: Optional[Decimal] = None
    moneda: Optional[str] = None

