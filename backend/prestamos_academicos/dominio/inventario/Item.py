"""
<<root>> Item
Generado a partir del bounded context: inventario
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from ..errores import TransicionInvalida
from ..shared_kernel import ItemId
from .EstadoItem import EstadoItem, transicion_permitida


@dataclass
class Item:  # clase abstracta (root agregado)
    id: Optional[ItemId] = None
    codigo: Optional[str] = None
    nombre: Optional[str] = None
    categoria: Optional[str] = None
    estado: Optional[EstadoItem] = EstadoItem.DISPONIBLE

    # Nombre del tipo en el catálogo (LIBRO, EQUIPO, ...). Lo fija cada subclase.
    TIPO = "ITEM"

    def _cambiar_estado(self, nuevo: EstadoItem) -> None:
        actual = self.estado or EstadoItem.DISPONIBLE
        if actual == nuevo:
            raise TransicionInvalida(f"El ítem ya está en estado {nuevo.value}.")
        if not transicion_permitida(actual, nuevo):
            raise TransicionInvalida(
                f"No se puede pasar de {actual.value} a {nuevo.value}."
            )
        self.estado = nuevo

    def marcarPrestado(self):
        self._cambiar_estado(EstadoItem.PRESTADO)

    def marcarDisponible(self):
        self._cambiar_estado(EstadoItem.DISPONIBLE)

    def marcarReservado(self):
        self._cambiar_estado(EstadoItem.RESERVADO)

    def marcarExtraviado(self):
        self._cambiar_estado(EstadoItem.EXTRAVIADO)

    def enviarAMantenimiento(self):
        self._cambiar_estado(EstadoItem.EN_MANTENIMIENTO)

    def darDeBaja(self):
        self._cambiar_estado(EstadoItem.DADO_DE_BAJA)

    def estaDisponible(self) -> bool:
        return self.estado == EstadoItem.DISPONIBLE

    def atributosEspecificos(self) -> Dict[str, Any]:
        """Atributos propios de la subclase (se persisten como JSON)."""
        return {}
