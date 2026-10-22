"""<<Repository Interface>> IModalidadRepository (puerto del dominio)."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional

from .Modalidad import Modalidad


class IModalidadRepository(ABC):
    @abstractmethod
    def save(self, modalidad: Modalidad) -> Modalidad: ...

    @abstractmethod
    def find_by_id(self, modalidad_id: int) -> Optional[Modalidad]: ...

    @abstractmethod
    def find_by_nombre(self, nombre: str) -> Optional[Modalidad]: ...

    @abstractmethod
    def listar(self) -> List[Modalidad]: ...
