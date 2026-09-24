"""
<<root>> Prestamo
Generado a partir del bounded context: prestamos
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date, datetime
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
    estado: Optional[EstadoPrestamo] = None

    def registrarDevolucion(self):
        """TODO: implementar registrarDevolucion()"""
        raise NotImplementedError

    def renovar(self):
        """TODO: implementar renovar()"""
        raise NotImplementedError

    def calcularFechaLimite(self):
        """TODO: implementar calcularFechaLimite()"""
        raise NotImplementedError

