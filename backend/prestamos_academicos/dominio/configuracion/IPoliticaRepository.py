"""<<Repository Interface>> IPoliticaRepository (puerto del dominio)."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional

from ..shared_kernel import RolUsuario
from .PoliticaServicio import PoliticaServicio


class IPoliticaRepository(ABC):
    @abstractmethod
    def save(self, politica: PoliticaServicio) -> PoliticaServicio: ...

    @abstractmethod
    def find_by_rol(self, rol: RolUsuario) -> Optional[PoliticaServicio]: ...

    @abstractmethod
    def find_by_id(self, politica_id: int) -> Optional[PoliticaServicio]: ...

    @abstractmethod
    def listar(self) -> List[PoliticaServicio]: ...
