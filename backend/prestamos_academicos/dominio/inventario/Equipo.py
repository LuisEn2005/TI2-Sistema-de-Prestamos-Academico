"""
<<entity>> Equipo
Generado a partir del bounded context: inventario
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional
from .Item import Item


@dataclass
class Equipo(Item):
    numeroSerie: Optional[str] = None
    marcaModelo: Optional[str] = None

    TIPO = "EQUIPO"

    def atributosEspecificos(self) -> Dict[str, Any]:
        return {"numeroSerie": self.numeroSerie, "marcaModelo": self.marcaModelo}
