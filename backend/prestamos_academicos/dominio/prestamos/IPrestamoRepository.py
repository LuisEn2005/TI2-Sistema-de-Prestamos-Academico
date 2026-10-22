"""<<Repository Interface>> IPrestamoRepository (puerto del dominio)."""
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional, Tuple

from .Prestamo import Prestamo


class IPrestamoRepository(ABC):
    @abstractmethod
    def save(self, prestamo: Prestamo) -> Prestamo: ...

    @abstractmethod
    def find_by_id(self, prestamo_id: int) -> Optional[Prestamo]: ...

    @abstractmethod
    def find_activos(self) -> List[Prestamo]: ...

    @abstractmethod
    def buscar(self, *, usuario_id: Optional[int] = None, estado: Optional[str] = None,
               hoy: Optional[date] = None, pagina: int = 1,
               limite: int = 20) -> Tuple[List[Prestamo], int]:
        """`estado`: activo, vencido (activo con fecha límite pasada respecto de `hoy`) o devuelto."""

    @abstractmethod
    def contar_items_activos(self, usuario_id: int) -> int:
        """Ítems que el usuario tiene hoy en préstamos sin devolver (base del cupo, RF13)."""
