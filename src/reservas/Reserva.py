"""
<<root>> Reserva
Generado a partir del bounded context: reservas
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date, datetime
from ..shared_kernel import ReservaId, UsuarioId, ItemId
from .EstadoReserva import EstadoReserva


@dataclass
class Reserva:
    id: Optional[ReservaId] = None
    usuarioId: Optional[UsuarioId] = None
    itemId: Optional[ItemId] = None
    fechaSolicitud: Optional[date] = None
    fechaReserva: Optional[date] = None
    estado: Optional[EstadoReserva] = None

    def confirmar(self):
        """TODO: implementar confirmar()"""
        raise NotImplementedError

    def expirar(self):
        """TODO: implementar expirar()"""
        raise NotImplementedError

    def cancelar(self):
        """TODO: implementar cancelar()"""
        raise NotImplementedError

