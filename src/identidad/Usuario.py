"""
<<root>> Usuario
Generado a partir del bounded context: identidad
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from ..shared_kernel import UsuarioId, RolUsuario
from .PerfilEstudiante import PerfilEstudiante
from .PerfilDocente import PerfilDocente
from .PerfilAdministrativo import PerfilAdministrativo
from .PerfilGestorInventario import PerfilGestorInventario


@dataclass
class Usuario:
    id: Optional[UsuarioId] = None
    nombre: Optional[str] = None
    correoElectronico: Optional[str] = None
    roles: Optional[List[RolUsuario]] = None
    tieneSancionActivaCache: Optional[bool] = None
    perfilEstudiante: Optional[Optional[PerfilEstudiante]] = None
    perfilDocente: Optional[Optional[PerfilDocente]] = None
    perfilAdministrativo: Optional[Optional[PerfilAdministrativo]] = None
    perfilGestorInventario: Optional[Optional[PerfilGestorInventario]] = None

    def tieneSancionActiva(self):
        """TODO: implementar tieneSancionActiva() : bool"""
        raise NotImplementedError

    def tieneRol(self):
        """TODO: implementar tieneRol(rol: RolUsuario) : bool"""
        raise NotImplementedError

