"""Dominio de configuracion: politicas de servicio, sancion y modalidades."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

from ..compartido import ModalidadId, PoliticaServicioId, RolUsuario


@dataclass
class Modalidad:
    id: Optional[ModalidadId] = None
    nombre: Optional[str] = None
    activo: Optional[bool] = True


@dataclass
class PoliticaServicio:
    id: Optional[PoliticaServicioId] = None
    rolAplicable: Optional[RolUsuario] = None
    modalidadId: Optional[ModalidadId] = None
    modalidadNombre: Optional[str] = None
    maxItemsSimultaneos: Optional[int] = None
    diasPrestamo: Optional[int] = None
    diasSancionPorDiaAtraso: int = 1
    tiposRecursoPermitidos: List[str] = field(default_factory=list)

    def tiposPermitidos(self) -> List[str]:
        return [tipo.strip().upper() for tipo in (self.tiposRecursoPermitidos or [])]

    def permiteTipo(self, tipo: str) -> bool:
        return (tipo or "").upper() in self.tiposPermitidos()

    def cupoRestante(self, itemsEnPrestamo: int) -> int:
        return max(0, (self.maxItemsSimultaneos or 0) - itemsEnPrestamo)


class IPoliticaRepository(ABC):
    @abstractmethod
    def save(self, politica: PoliticaServicio) -> PoliticaServicio: ...

    @abstractmethod
    def find_by_rol_y_modalidad(
            self, rol: RolUsuario, modalidad_id: int) -> Optional[PoliticaServicio]: ...

    @abstractmethod
    def listar_por_rol(self, rol: RolUsuario) -> List[PoliticaServicio]: ...

    @abstractmethod
    def find_by_id(self, politica_id: int) -> Optional[PoliticaServicio]: ...

    @abstractmethod
    def listar(self) -> List[PoliticaServicio]: ...


class IModalidadRepository(ABC):
    @abstractmethod
    def save(self, modalidad: Modalidad) -> Modalidad: ...

    @abstractmethod
    def find_by_id(self, modalidad_id: int) -> Optional[Modalidad]: ...

    @abstractmethod
    def find_by_nombre(self, nombre: str) -> Optional[Modalidad]: ...

    @abstractmethod
    def listar(self) -> List[Modalidad]: ...
