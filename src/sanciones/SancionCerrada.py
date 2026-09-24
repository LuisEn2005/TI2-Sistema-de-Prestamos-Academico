"""
<<domain event>> SancionCerrada
Generado a partir del bounded context: sanciones
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from ..shared_kernel import SancionId, UsuarioId


@dataclass
class SancionCerrada:
    sancionId: Optional[SancionId] = None
    usuarioId: Optional[UsuarioId] = None

