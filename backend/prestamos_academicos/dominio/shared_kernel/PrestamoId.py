"""
<<valueobject>> PrestamoId
Generado a partir del bounded context: shared_kernel
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID


@dataclass
class PrestamoId:
    valor: Optional[UUID] = None

