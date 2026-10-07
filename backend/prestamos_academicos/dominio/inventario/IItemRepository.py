"""<<Repository Interface>> IItemRepository (puerto del dominio)."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from .EstadoItem import EstadoItem
from .Item import Item


class IItemRepository(ABC):
    @abstractmethod
    def save(self, item: Item) -> Item: ...

    @abstractmethod
    def find_by_id(self, item_id: int) -> Optional[Item]: ...

    @abstractmethod
    def find_by_codigo(self, codigo: str) -> Optional[Item]: ...

    @abstractmethod
    def find_disponible(self) -> List[Item]: ...

    @abstractmethod
    def buscar(self, *, texto=None, tipo=None, categoria=None, estado=None,
               pagina=1, limite=20) -> Tuple[List[Item], int]: ...

    @abstractmethod
    def categorias(self) -> List[str]: ...

    @abstractmethod
    def cambiar_estado_si(self, item_id: int, desde: EstadoItem, hacia: EstadoItem) -> bool:
        """Cambio atómico (compare-and-set). True si se aplicó."""
