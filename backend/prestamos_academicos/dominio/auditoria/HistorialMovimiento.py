"""
<<root>> HistorialMovimiento
Generado a partir del bounded context: auditoria
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date, datetime
from ..shared_kernel import UsuarioId
from .TipoEvento import TipoEvento


@dataclass
class HistorialMovimiento:
    id: Optional[int] = None
    tipoEvento: Optional[TipoEvento] = None
    fechaEvento: Optional[datetime] = None
    detalle: Optional[str] = None
    entidadOrigenId: Optional[str] = None
    usuarioResponsableId: Optional[UsuarioId] = None

