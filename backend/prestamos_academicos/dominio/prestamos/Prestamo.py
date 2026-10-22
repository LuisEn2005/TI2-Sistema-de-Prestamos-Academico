"""
<<root>> Prestamo
Entrega de uno o más ítems a un usuario bajo una modalidad, con fecha límite
calculada según la política del perfil y devolución con condición por ítem.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional

from ..errores import ErrorDominio
from ..shared_kernel import ItemId, PrestamoId, ReservaId, RolUsuario, UsuarioId
from .CondicionDevolucion import CondicionDevolucion
from .DetallePrestamo import DetallePrestamo
from .EstadoPrestamo import EstadoPrestamo
from .ModalidadSnapshot import ModalidadSnapshot
from .PrestamoDevuelto import PrestamoDevuelto
from .PrestamoDevueltoTarde import PrestamoDevueltoTarde


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
    # Eventos pendientes de publicar; los consumirán sanciones y auditoría (Sprints 5 y 6).
    eventos: List[object] = field(default_factory=list, repr=False, compare=False)

    # -- creación ----------------------------------------------------------
    @classmethod
    def entregar(cls, *, usuarioId: UsuarioId, rol: RolUsuario, modalidad: ModalidadSnapshot,
                 diasPolitica: int, items: Iterable[ItemId], ahora: datetime,
                 hoy: date) -> "Prestamo":
        """Crea un préstamo activo con su fecha límite. `hoy` es la fecha local de la escuela."""
        items = list(items)
        if not items:
            raise ErrorDominio("Un préstamo debe incluir al menos un ítem.")
        if len({i.valor for i in items}) != len(items):
            raise ErrorDominio("Un ítem no puede repetirse dentro del mismo préstamo.")
        prestamo = cls(
            usuarioId=usuarioId, rolSolicitante=rol, modalidad=modalidad, fechaEntrega=ahora,
            detalles=[DetallePrestamo(itemId=i) for i in items])
        prestamo.fechaDevolucionEsperada = prestamo.calcularFechaLimite(hoy, diasPolitica)
        return prestamo

    def calcularFechaLimite(self, hoy: date, diasPolitica: int) -> date:
        if self.modalidad is None or not self.modalidad.diasPlazo or self.modalidad.diasPlazo < 1:
            raise ErrorDominio("El préstamo necesita una modalidad con plazo en días.")
        if diasPolitica < 1:
            raise ErrorDominio("La política del perfil debe permitir al menos un día de préstamo.")
        return hoy + timedelta(days=self.modalidad.diasEfectivos(diasPolitica))

    # -- consulta ----------------------------------------------------------
    def diasAtraso(self, hoy: date) -> int:
        """Días de retraso respecto de la fecha límite (0 si no hay fecha límite o llegó a tiempo)."""
        if self.fechaDevolucionEsperada is None:
            return 0
        return max(0, (hoy - self.fechaDevolucionEsperada).days)

    def estaVencido(self, hoy: date) -> bool:
        return self.estado == EstadoPrestamo.ACTIVO and self.diasAtraso(hoy) > 0

    # -- devolución --------------------------------------------------------
    def registrarDevolucion(self, condiciones: Dict[int, CondicionDevolucion], *,
                            hoy: date, fecha: Optional[datetime] = None,
                            observaciones: Optional[Dict[int, str]] = None) -> None:
        """Cierra el préstamo con la condición de cada ítem (RF11).

        `condiciones` asocia el id de cada ítem con su condición y debe cubrir exactamente
        los ítems del préstamo. `hoy` es la fecha local de la escuela, para medir el atraso.
        """
        if self.estado == EstadoPrestamo.DEVUELTO:
            raise ErrorDominio("El préstamo ya fue devuelto.")
        esperados = {d.itemId.valor for d in self.detalles}
        if set(condiciones) != esperados:
            raise ErrorDominio(
                "Debe indicar la condición de cada ítem del préstamo, sin omitir ni añadir otros.")
        observaciones = observaciones or {}
        for detalle in self.detalles:
            detalle.condicion = CondicionDevolucion(condiciones[detalle.itemId.valor])
            detalle.observacion = observaciones.get(detalle.itemId.valor)
        atraso = self.diasAtraso(hoy)
        self.fechaDevolucionReal = fecha or datetime.now(timezone.utc)
        self.estado = EstadoPrestamo.DEVUELTO
        for detalle in self.detalles:
            self.eventos.append(PrestamoDevuelto(
                prestamoId=self.id, itemId=detalle.itemId, condicion=detalle.condicion))
        if atraso > 0:
            self.eventos.append(PrestamoDevueltoTarde(
                prestamoId=self.id, usuarioId=self.usuarioId, diasAtraso=atraso))

    def renovar(self):
        """Se implementa en el Sprint 4 (RF12)."""
        raise NotImplementedError
