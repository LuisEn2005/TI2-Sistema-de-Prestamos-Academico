"""
<<entity>> PerfilAdministrativo
Generado a partir del bounded context: identidad
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from ..shared_kernel import PoliticaServicioId


@dataclass
class PerfilAdministrativo:
    codigoEmpleado: Optional[str] = None
    cargoAdministrativo: Optional[str] = None
    politicaServicioId: Optional[PoliticaServicioId] = None

