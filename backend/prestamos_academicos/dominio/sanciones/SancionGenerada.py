"""
<<domain event>> SancionGenerada
Generado a partir del bounded context: sanciones
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from ..shared_kernel import SancionId, UsuarioId


@dataclass
class SancionGenerada:
    sancionId: Optional[SancionId] = None
    usuarioId: Optional[UsuarioId] = None

