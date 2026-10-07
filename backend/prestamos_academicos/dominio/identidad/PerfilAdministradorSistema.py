"""Perfil que otorga la administración integral del sistema."""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class PerfilAdministradorSistema:
    codigoEmpleado: Optional[str] = None
    fechaAsignacion: Optional[date] = None
