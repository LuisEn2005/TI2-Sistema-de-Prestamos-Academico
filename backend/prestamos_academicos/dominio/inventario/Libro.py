"""
<<entity>> Libro
Generado a partir del bounded context: inventario
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional
from .Item import Item


@dataclass
class Libro(Item):
    isbn: Optional[str] = None
    autor: Optional[str] = None
    editorial: Optional[str] = None

    TIPO = "LIBRO"

    def atributosEspecificos(self) -> Dict[str, Any]:
        return {"isbn": self.isbn, "autor": self.autor, "editorial": self.editorial}
