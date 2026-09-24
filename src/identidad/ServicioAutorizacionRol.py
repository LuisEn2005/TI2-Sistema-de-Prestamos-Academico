"""
<<domain service>> ServicioAutorizacionRol
Generado a partir del bounded context: identidad
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from ..shared_kernel import RolUsuario
from .Permiso import Permiso


@dataclass
class ServicioAutorizacionRol:
    pass

    def permisosDe(self):
        """TODO: implementar permisosDe(rol: RolUsuario) : List<Permiso>"""
        raise NotImplementedError

    def tienePermiso(self):
        """TODO: implementar tienePermiso(rol: RolUsuario, permiso: Permiso) : bool"""
        raise NotImplementedError

