"""
<<root>> Sancion
Generado a partir del bounded context: sanciones
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date, datetime
from ..shared_kernel import SancionId, UsuarioId, PrestamoId
from .OrigenSancion import OrigenSancion
from .EstadoSancion import EstadoSancion
from .Monto import Monto


@dataclass
class Sancion:
    id: Optional[SancionId] = None
    usuarioId: Optional[UsuarioId] = None
    prestamoId: Optional[PrestamoId] = None
    origen: Optional[OrigenSancion] = None
    motivo: Optional[str] = None
    monto: Optional[Monto] = None
    fechaInicio: Optional[date] = None
    fechaFin: Optional[date] = None
    estado: Optional[EstadoSancion] = None

    def levantar(self):
        """TODO: implementar levantar()"""
        raise NotImplementedError

