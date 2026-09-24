"""
<<root>> Item
Generado a partir del bounded context: inventario
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from ..shared_kernel import ItemId
from .EstadoItem import EstadoItem


@dataclass
class Item:  # clase abstracta (root agregado)
    id: Optional[ItemId] = None
    codigo: Optional[str] = None
    nombre: Optional[str] = None
    categoria: Optional[str] = None
    estado: Optional[EstadoItem] = None

    def marcarPrestado(self):
        """TODO: implementar marcarPrestado()"""
        raise NotImplementedError

    def marcarDisponible(self):
        """TODO: implementar marcarDisponible()"""
        raise NotImplementedError

    def marcarReservado(self):
        """TODO: implementar marcarReservado()"""
        raise NotImplementedError

    def marcarExtraviado(self):
        """TODO: implementar marcarExtraviado()"""
        raise NotImplementedError

