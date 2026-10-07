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
from .PerfilAdministradorSistema import PerfilAdministradorSistema

_ROLES_PRESTATARIOS = (RolUsuario.DOCENTE, RolUsuario.ADMINISTRATIVO)


@dataclass
class Usuario:
    id: Optional[UsuarioId] = None
    nombre: Optional[str] = None
    correoElectronico: Optional[str] = None
    roles: Optional[List[RolUsuario]] = None
    tieneSancionActivaCache: Optional[bool] = False
    activo: bool = True
    versionSesion: int = 0
    perfilEstudiante: Optional[PerfilEstudiante] = None
    perfilDocente: Optional[PerfilDocente] = None
    perfilAdministrativo: Optional[PerfilAdministrativo] = None
    perfilGestorInventario: Optional[PerfilGestorInventario] = None
    perfilAdministradorSistema: Optional[PerfilAdministradorSistema] = None

    def invalidarSesiones(self) -> None:
        self.versionSesion += 1

    def sincronizarRoles(self) -> None:
        """Los roles se deducen de los perfiles presentes (patrón Party/Role)."""
        pares = (
            (RolUsuario.ESTUDIANTE, self.perfilEstudiante),
            (RolUsuario.DOCENTE, self.perfilDocente),
            (RolUsuario.ADMINISTRATIVO, self.perfilAdministrativo),
            (RolUsuario.GESTOR_INVENTARIO, self.perfilGestorInventario),
            (RolUsuario.ADMINISTRADOR_SISTEMA, self.perfilAdministradorSistema),
        )
        self.roles = [rol for rol, perfil in pares if perfil is not None]

    def tieneSancionActiva(self) -> bool:
        return bool(self.tieneSancionActivaCache)

    def tieneRol(self, rol: RolUsuario) -> bool:
        return RolUsuario(rol) in (self.roles or [])

    def esPrestatario(self) -> bool:
        """Puede recibir recursos: estudiante, docente o administrativo."""
        return any(self.tieneRol(r) for r in (RolUsuario.ESTUDIANTE, *_ROLES_PRESTATARIOS))

    def tieneVinculacionVigente(self) -> bool:
        """Tiene al menos una afiliación académica vigente (RF02)."""
        vinculaciones = (
            self.tieneRol(RolUsuario.ESTUDIANTE)
            and self.perfilEstudiante is not None
            and self.perfilEstudiante.matriculaVigente,
            self.tieneRol(RolUsuario.DOCENTE)
            and self.perfilDocente is not None
            and self.perfilDocente.vinculacionVigente,
            self.tieneRol(RolUsuario.ADMINISTRATIVO)
            and self.perfilAdministrativo is not None
            and self.perfilAdministrativo.vinculacionVigente,
        )
        return any(vinculaciones)

    def estaHabilitado(self) -> bool:
        """RF02 (parcial en Sprint 2): activo, vinculado y sin sanción activa."""
        return (
            self.activo
            and self.esPrestatario()
            and self.tieneVinculacionVigente()
            and not self.tieneSancionActiva()
        )

    def motivoNoHabilitado(self) -> Optional[str]:
        if not self.activo:
            return "El usuario está desactivado."
        if not self.esPrestatario():
            return "El usuario no tiene un rol que permita recibir préstamos."
        if not self.tieneVinculacionVigente():
            return "El usuario no tiene matrícula o vinculación vigente."
        if self.tieneSancionActiva():
            return "El usuario tiene una sanción activa."
        return None
