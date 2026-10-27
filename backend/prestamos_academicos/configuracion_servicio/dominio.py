"""Dominio de configuracion: politicas de servicio, sancion y modalidades."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from ..compartido import (
    ModalidadId, PoliticaSancionId, PoliticaServicioId, RolUsuario,
)
from ..prestamos import ModalidadSnapshot
from ..sanciones import OrigenSancion


@dataclass
class Modalidad:
    id: Optional[ModalidadId] = None
    nombre: Optional[str] = None
    diasPlazoDefault: Optional[int] = None
    activo: Optional[bool] = True

    def snapshot(self) -> ModalidadSnapshot:
        return ModalidadSnapshot(self.id, self.nombre, self.diasPlazoDefault)


@dataclass
class PoliticaServicio:
    id: Optional[PoliticaServicioId] = None
    rolAplicable: Optional[RolUsuario] = None
    maxItemsSimultaneos: Optional[int] = None
    diasPrestamoDefault: Optional[int] = None
    diasGraciaReserva: Optional[int] = None
    tiposRecursoPermitidos: Optional[str] = None

    def tiposPermitidos(self) -> List[str]:
        return [
            tipo.strip().upper()
            for tipo in (self.tiposRecursoPermitidos or "").split(",")
            if tipo.strip()
        ]

    def permiteTipo(self, tipo: str) -> bool:
        return (tipo or "").upper() in self.tiposPermitidos()

    def cupoRestante(self, itemsEnPrestamo: int) -> int:
        return max(0, (self.maxItemsSimultaneos or 0) - itemsEnPrestamo)


@dataclass
class PoliticaSancion:
    id: Optional[PoliticaSancionId] = None
    origenAplicable: Optional[OrigenSancion] = None
    diasBase: Optional[int] = None
    diasPorDiaAtraso: Optional[int] = None


class IPoliticaRepository(ABC):
    @abstractmethod
    def save(self, politica: PoliticaServicio) -> PoliticaServicio: ...

    @abstractmethod
    def find_by_rol(self, rol: RolUsuario) -> Optional[PoliticaServicio]: ...

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
