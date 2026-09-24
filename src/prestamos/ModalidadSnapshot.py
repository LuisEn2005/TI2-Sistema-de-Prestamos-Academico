"""
<<valueobject>> ModalidadSnapshot
Generado a partir del bounded context: prestamos
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from ..shared_kernel import ModalidadId


@dataclass
class ModalidadSnapshot:
    modalidadOrigenId: Optional[ModalidadId] = None
    nombre: Optional[str] = None
    diasPlazo: Optional[int] = None

