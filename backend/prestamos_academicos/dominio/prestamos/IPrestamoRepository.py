"""<<Repository Interface>> IPrestamoRepository (puerto del dominio)."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional

from .Prestamo import Prestamo


class IPrestamoRepository(ABC):
    @abstractmethod
    def save(self, prestamo: Prestamo) -> Prestamo: ...

    @abstractmethod
    def find_by_id(self, prestamo_id: int) -> Optional[Prestamo]: ...

    @abstractmethod
    def find_activos(self) -> List[Prestamo]: ...

    @abstractmethod
    def listar(self, usuario_id: Optional[int] = None) -> List[Prestamo]: ...
