"""
<<root>> PoliticaServicio
Generado a partir del bounded context: configuracion
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from ..shared_kernel import PoliticaServicioId, RolUsuario


@dataclass
class PoliticaServicio:
    id: Optional[PoliticaServicioId] = None
    rolAplicable: Optional[RolUsuario] = None
    maxItemsSimultaneos: Optional[int] = None
    diasPrestamoDefault: Optional[int] = None
    diasGraciaReserva: Optional[int] = None
    tiposRecursoPermitidos: Optional[str] = None


    def tiposPermitidos(self) -> List[str]:
        return [t.strip().upper() for t in (self.tiposRecursoPermitidos or "").split(",") if t.strip()]

    def permiteTipo(self, tipo: str) -> bool:
        return (tipo or "").upper() in self.tiposPermitidos()

    def cupoRestante(self, itemsEnPrestamo: int) -> int:
        """Ítems que aún puede recibir un usuario con `itemsEnPrestamo` ítems activos (RF13)."""
        return max(0, (self.maxItemsSimultaneos or 0) - itemsEnPrestamo)
