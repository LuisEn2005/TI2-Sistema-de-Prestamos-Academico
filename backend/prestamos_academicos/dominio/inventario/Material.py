"""
<<entity>> Material
Generado a partir del bounded context: inventario
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional
from .Item import Item


@dataclass
class Material(Item):
    tipoMaterial: Optional[str] = None
    unidadMedida: Optional[str] = None

    TIPO = "MATERIAL"

    def atributosEspecificos(self) -> Dict[str, Any]:
        return {"tipoMaterial": self.tipoMaterial, "unidadMedida": self.unidadMedida}
