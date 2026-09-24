"""
<<domain event>> PrestamoDevueltoTarde
Generado a partir del bounded context: prestamos
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from ..shared_kernel import PrestamoId, UsuarioId


@dataclass
class PrestamoDevueltoTarde:
    prestamoId: Optional[PrestamoId] = None
    usuarioId: Optional[UsuarioId] = None
    diasAtraso: Optional[int] = None

