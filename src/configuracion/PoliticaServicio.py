"""
<<root>> PoliticaServicio
Generado a partir del bounded context: configuracion
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from ..shared_kernel import PoliticaServicioId, RolUsuario


@dataclass
class PoliticaServicio:
    id: Optional[PoliticaServicioId] = None
    rolAplicable: Optional[RolUsuario] = None
    maxItemsSimultaneos: Optional[int] = None
    diasPrestamoDefault: Optional[int] = None
    diasGraciaReserva: Optional[int] = None
    tiposRecursoPermitidos: Optional[str] = None

