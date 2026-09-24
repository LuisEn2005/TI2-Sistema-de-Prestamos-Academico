"""
<<entity>> PerfilGestorInventario
Generado a partir del bounded context: identidad
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date, datetime


@dataclass
class PerfilGestorInventario:
    codigoEmpleado: Optional[str] = None
    areaResponsable: Optional[str] = None
    fechaAsignacion: Optional[date] = None

