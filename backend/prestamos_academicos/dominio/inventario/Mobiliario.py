"""
<<entity>> Mobiliario
Generado a partir del bounded context: inventario
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional
from .Item import Item


@dataclass
class Mobiliario(Item):
    tipoMobiliario: Optional[str] = None
    ubicacionHabitual: Optional[str] = None

    TIPO = "MOBILIARIO"

    def atributosEspecificos(self) -> Dict[str, Any]:
        return {"tipoMobiliario": self.tipoMobiliario, "ubicacionHabitual": self.ubicacionHabitual}
