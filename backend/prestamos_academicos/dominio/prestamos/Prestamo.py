"""
<<root>> Prestamo
Generado a partir del bounded context: prestamos
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date, datetime, timezone
from ..errores import ErrorDominio
from .DetallePrestamo import DetallePrestamo
from ..shared_kernel import PrestamoId, UsuarioId, ReservaId
from .EstadoPrestamo import EstadoPrestamo


@dataclass
class Prestamo:
    id: Optional[PrestamoId] = None
    usuarioId: Optional[UsuarioId] = None
    reservaId: Optional[ReservaId] = None
    fechaEntrega: Optional[date] = None
    fechaDevolucionEsperada: Optional[date] = None
    fechaDevolucionReal: Optional[date] = None
    estado: Optional[EstadoPrestamo] = EstadoPrestamo.ACTIVO
    detalles: List[DetallePrestamo] = field(default_factory=list)

    def registrarDevolucion(self, fecha=None):
        """Cierra el préstamo. Fecha, condición y atraso se completan en el Sprint 3."""
        if self.estado == EstadoPrestamo.DEVUELTO:
            raise ErrorDominio("El préstamo ya fue devuelto.")
        self.fechaDevolucionReal = fecha or datetime.now(timezone.utc)
        self.estado = EstadoPrestamo.DEVUELTO

    def renovar(self):
        """TODO: implementar renovar()"""
        raise NotImplementedError

    def calcularFechaLimite(self):
        """TODO: implementar calcularFechaLimite()"""
        raise NotImplementedError

