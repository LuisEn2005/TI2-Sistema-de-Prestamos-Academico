"""
<<root>> PoliticaSancion
Generado a partir del bounded context: configuracion
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from ..shared_kernel import PoliticaSancionId
from ..sanciones import OrigenSancion


@dataclass
class PoliticaSancion:
    id: Optional[PoliticaSancionId] = None
    origenAplicable: Optional[OrigenSancion] = None
    diasBase: Optional[int] = None
    diasPorDiaAtraso: Optional[int] = None

