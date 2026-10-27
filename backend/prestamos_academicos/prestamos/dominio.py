"""Dominio de prestamos: entrega, plazo y devolucion de varios items."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Dict, Iterable, List, Optional, Tuple

from ..compartido import (
    ErrorDominio, ItemId, ModalidadId, PrestamoId, ReservaId, RolUsuario, UsuarioId,
)


class CondicionDevolucion(str, Enum):
    BUEN_ESTADO = "BUEN_ESTADO"
    DANADO = "DANADO"
    PERDIDO = "PERDIDO"


class EstadoPrestamo(str, Enum):
    ACTIVO = "ACTIVO"
    DEVUELTO = "DEVUELTO"
    VENCIDO = "VENCIDO"


@dataclass
class DetallePrestamo:
    id: Optional[int] = None
    itemId: Optional[ItemId] = None
    condicion: Optional[CondicionDevolucion] = None
    observacion: Optional[str] = None


@dataclass(frozen=True)
class ModalidadSnapshot:
    modalidadOrigenId: Optional[ModalidadId] = None
    nombre: Optional[str] = None
    diasPlazo: Optional[int] = None

    def diasEfectivos(self, diasPolitica: int) -> int:
        return min(self.diasPlazo, diasPolitica)


@dataclass
class PrestamoRealizado:
    prestamoId: Optional[PrestamoId] = None
    itemId: Optional[ItemId] = None
    fecha: Optional[datetime] = None


@dataclass
class PrestamoDevuelto:
    prestamoId: Optional[PrestamoId] = None
    itemId: Optional[ItemId] = None
    condicion: Optional[CondicionDevolucion] = None


@dataclass
class PrestamoDevueltoTarde:
    prestamoId: Optional[PrestamoId] = None
    usuarioId: Optional[UsuarioId] = None
    diasAtraso: Optional[int] = None


@dataclass
class Prestamo:
    id: Optional[PrestamoId] = None
    usuarioId: Optional[UsuarioId] = None
    reservaId: Optional[ReservaId] = None
    rolSolicitante: Optional[RolUsuario] = None
    modalidad: Optional[ModalidadSnapshot] = None
    fechaEntrega: Optional[datetime] = None
    fechaDevolucionEsperada: Optional[date] = None
    fechaDevolucionReal: Optional[datetime] = None
    estado: Optional[EstadoPrestamo] = EstadoPrestamo.ACTIVO
    detalles: List[DetallePrestamo] = field(default_factory=list)
    eventos: List[object] = field(default_factory=list, repr=False, compare=False)

    @classmethod
    def entregar(cls, *, usuarioId: UsuarioId, rol: RolUsuario,
                 modalidad: ModalidadSnapshot, diasPolitica: int,
                 items: Iterable[ItemId], ahora: datetime, hoy: date) -> "Prestamo":
        items = list(items)
        if not items:
            raise ErrorDominio("Un préstamo debe incluir al menos un ítem.")
        if len({item.valor for item in items}) != len(items):
            raise ErrorDominio("Un ítem no puede repetirse dentro del mismo préstamo.")
        prestamo = cls(
            usuarioId=usuarioId,
            rolSolicitante=rol,
            modalidad=modalidad,
            fechaEntrega=ahora,
            detalles=[DetallePrestamo(itemId=item) for item in items],
        )
        prestamo.fechaDevolucionEsperada = prestamo.calcularFechaLimite(hoy, diasPolitica)
        return prestamo

    def calcularFechaLimite(self, hoy: date, diasPolitica: int) -> date:
        if self.modalidad is None or not self.modalidad.diasPlazo or self.modalidad.diasPlazo < 1:
            raise ErrorDominio("El préstamo necesita una modalidad con plazo en días.")
        if diasPolitica < 1:
            raise ErrorDominio("La política del perfil debe permitir al menos un día de préstamo.")
        return hoy + timedelta(days=self.modalidad.diasEfectivos(diasPolitica))

    def diasAtraso(self, hoy: date) -> int:
        if self.fechaDevolucionEsperada is None:
            return 0
        return max(0, (hoy - self.fechaDevolucionEsperada).days)

    def estaVencido(self, hoy: date) -> bool:
        return self.estado == EstadoPrestamo.ACTIVO and self.diasAtraso(hoy) > 0

    def registrarDevolucion(self, condiciones: Dict[int, CondicionDevolucion], *,
                            hoy: date, fecha: Optional[datetime] = None,
                            observaciones: Optional[Dict[int, str]] = None) -> None:
        if self.estado == EstadoPrestamo.DEVUELTO:
            raise ErrorDominio("El préstamo ya fue devuelto.")
        esperados = {detalle.itemId.valor for detalle in self.detalles}
        if set(condiciones) != esperados:
            raise ErrorDominio(
                "Debe indicar la condición de cada ítem del préstamo, sin omitir ni añadir otros."
            )
        observaciones = observaciones or {}
        for detalle in self.detalles:
            detalle.condicion = CondicionDevolucion(condiciones[detalle.itemId.valor])
            detalle.observacion = observaciones.get(detalle.itemId.valor)
        atraso = self.diasAtraso(hoy)
        self.fechaDevolucionReal = fecha or datetime.now(timezone.utc)
        self.estado = EstadoPrestamo.DEVUELTO
        for detalle in self.detalles:
            self.eventos.append(PrestamoDevuelto(
                prestamoId=self.id,
                itemId=detalle.itemId,
                condicion=detalle.condicion,
            ))
        if atraso > 0:
            self.eventos.append(PrestamoDevueltoTarde(
                prestamoId=self.id,
                usuarioId=self.usuarioId,
                diasAtraso=atraso,
            ))

    def renovar(self):
        """Planificado para el Sprint 4 (RF12)."""
        raise NotImplementedError


class IPrestamoRepository(ABC):
    @abstractmethod
    def save(self, prestamo: Prestamo) -> Prestamo: ...

    @abstractmethod
    def find_by_id(self, prestamo_id: int) -> Optional[Prestamo]: ...

    @abstractmethod
    def find_activos(self) -> List[Prestamo]: ...

    @abstractmethod
    def buscar(self, *, usuario_id: Optional[int] = None,
               estado: Optional[str] = None, hoy: Optional[date] = None,
               pagina: int = 1, limite: int = 20) -> Tuple[List[Prestamo], int]: ...

    @abstractmethod
    def contar_items_activos(self, usuario_id: int) -> int: ...
