"""
<<root>> Modalidad
Generado a partir del bounded context: configuracion
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from ..shared_kernel import ModalidadId


@dataclass
class Modalidad:
    id: Optional[ModalidadId] = None
    nombre: Optional[str] = None
    diasPlazoDefault: Optional[int] = None
    activo: Optional[bool] = None

