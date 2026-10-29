"""Dominio simple de sanciones (RF14-RF16)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from ..compartido import ErrorDominio, PrestamoId, SancionId, UsuarioId


class EstadoSancion(str, Enum):
    ACTIVA = "ACTIVA"
    CERRADA = "CERRADA"


class OrigenSancion(str, Enum):
    RETRASO = "RETRASO"
    DANO = "DANO"
    PERDIDA = "PERDIDA"


@dataclass(frozen=True)
class Monto:
    cantidad: Decimal
    moneda: str = "PEN"


@dataclass
class Sancion:
    id: Optional[SancionId] = None
    usuarioId: Optional[UsuarioId] = None
    prestamoId: Optional[PrestamoId] = None
    creadaPorUsuarioId: Optional[UsuarioId] = None
    origen: Optional[OrigenSancion] = None
    motivo: Optional[str] = None
    monto: Optional[Monto] = None
    fechaInicio: Optional[date] = None
    fechaFin: Optional[date] = None
    estado: EstadoSancion = EstadoSancion.ACTIVA
    cerradaEn: Optional[datetime] = None
    resolucion: Optional[str] = None

    @classmethod
    def porAtraso(cls, *, usuario_id, prestamo_id, dias_atraso, factor, hoy):
        if dias_atraso < 1 or factor < 1:
            raise ErrorDominio("El atraso y su factor de sanción deben ser positivos.")
        return cls(
            usuarioId=UsuarioId(usuario_id), prestamoId=PrestamoId(prestamo_id),
            origen=OrigenSancion.RETRASO,
            motivo=f"Devolución con {dias_atraso} día(s) de atraso.",
            fechaInicio=hoy,
            # El rango es inclusivo: una sanción de un día termina hoy.
            fechaFin=hoy + timedelta(days=dias_atraso * factor - 1),
        )

    @classmethod
    def manual(cls, *, usuario_id, actor_id, origen, motivo, hoy,
               dias=None, monto=None, prestamo_id=None):
        origen = OrigenSancion(origen)
        if origen not in (OrigenSancion.DANO, OrigenSancion.PERDIDA):
            raise ErrorDominio("Una sanción manual debe originarse por daño o pérdida.")
        if not motivo or not motivo.strip():
            raise ErrorDominio("El motivo de la sanción es obligatorio.")
        if dias is None and monto is None:
            raise ErrorDominio("Indique una duración o un monto para la sanción.")
        return cls(
            usuarioId=UsuarioId(usuario_id),
            prestamoId=PrestamoId(prestamo_id) if prestamo_id else None,
            creadaPorUsuarioId=UsuarioId(actor_id), origen=origen,
            motivo=motivo.strip(), monto=monto, fechaInicio=hoy,
            fechaFin=(hoy + timedelta(days=dias - 1)
                      if dias is not None else None),
        )

    def estaActiva(self, hoy: date) -> bool:
        return self.estado == EstadoSancion.ACTIVA and (
            self.fechaFin is None or hoy <= self.fechaFin)

    def vencio(self, hoy: date) -> bool:
        return self.estado == EstadoSancion.ACTIVA and bool(
            self.fechaFin and hoy > self.fechaFin)

    def cerrar(self, resolucion: str, ahora: datetime) -> None:
        if self.estado != EstadoSancion.ACTIVA:
            raise ErrorDominio("La sanción ya está cerrada.")
        if not resolucion or not resolucion.strip():
            raise ErrorDominio("Indique cómo se resolvió la sanción.")
        self.estado = EstadoSancion.CERRADA
        self.resolucion = resolucion.strip()
        self.cerradaEn = ahora


class ISancionRepository(ABC):
    @abstractmethod
    def save(self, sancion: Sancion) -> Sancion: ...

    @abstractmethod
    def find_by_id(self, sancion_id: int) -> Optional[Sancion]: ...

    @abstractmethod
    def listar(self, *, usuario_id=None, estado=None) -> List[Sancion]: ...

    @abstractmethod
    def sincronizar_vencidas(self, hoy: date, ahora: datetime, usuario_id=None) -> int: ...

    @abstractmethod
    def actualizar_cache_usuario(self, usuario_id: int) -> bool: ...


@dataclass
class SancionGenerada:
    sancionId: Optional[SancionId] = None
    usuarioId: Optional[UsuarioId] = None


@dataclass
class SancionCerrada:
    sancionId: Optional[SancionId] = None
    usuarioId: Optional[UsuarioId] = None
