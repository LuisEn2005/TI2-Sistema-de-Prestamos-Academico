"""
<<valueobject>> ModalidadSnapshot
Copia de la modalidad vigente al registrar el préstamo: si la configuración
cambia después, los préstamos ya registrados no se alteran.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from ..shared_kernel import ModalidadId


@dataclass(frozen=True)
class ModalidadSnapshot:
    modalidadOrigenId: Optional[ModalidadId] = None
    nombre: Optional[str] = None
    diasPlazo: Optional[int] = None

    def diasEfectivos(self, diasPolitica: int) -> int:
        """RN2: el plazo es el menor entre el de la modalidad y el de la política del perfil.

        La modalidad actúa como tope (p. ej. «en sala» dura un día aunque el perfil
        permita quince) y la política personaliza el plazo según quién presta.
        """
        return min(self.diasPlazo, diasPolitica)
