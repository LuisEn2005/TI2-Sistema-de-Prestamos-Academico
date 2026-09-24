"""
<<entity>> PerfilEstudiante
Generado a partir del bounded context: identidad
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from ..shared_kernel import PoliticaServicioId


@dataclass
class PerfilEstudiante:
    codigoEstudiante: Optional[str] = None
    matriculaVigente: Optional[bool] = None
    politicaServicioId: Optional[PoliticaServicioId] = None

