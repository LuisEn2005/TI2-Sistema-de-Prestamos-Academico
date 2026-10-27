"""Dominio de identidad: perfiles, roles, permisos y habilitacion."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Iterable, List, Optional, Set

from ..compartido import PoliticaServicioId, RolUsuario, UsuarioId


class Permiso(str, Enum):
    RESERVAR_ITEM = "RESERVAR_ITEM"
    SOLICITAR_PRESTAMO = "SOLICITAR_PRESTAMO"
    RENOVAR_PRESTAMO = "RENOVAR_PRESTAMO"
    CONSULTAR_HISTORIAL_PROPIO = "CONSULTAR_HISTORIAL_PROPIO"
    CONSULTAR_PRESTATARIOS = "CONSULTAR_PRESTATARIOS"
    REGISTRAR_ITEM_INVENTARIO = "REGISTRAR_ITEM_INVENTARIO"
    ACTUALIZAR_ESTADO_ITEM = "ACTUALIZAR_ESTADO_ITEM"
    CONFIRMAR_RESERVA = "CONFIRMAR_RESERVA"
    REGISTRAR_ENTREGA_PRESTAMO = "REGISTRAR_ENTREGA_PRESTAMO"
    REGISTRAR_DEVOLUCION_PRESTAMO = "REGISTRAR_DEVOLUCION_PRESTAMO"
    CONFIGURAR_POLITICAS = "CONFIGURAR_POLITICAS"
    GESTIONAR_USUARIOS_Y_ROLES = "GESTIONAR_USUARIOS_Y_ROLES"
    GENERAR_SANCION_MANUAL = "GENERAR_SANCION_MANUAL"
    LEVANTAR_SANCION = "LEVANTAR_SANCION"
    CONSULTAR_HISTORIAL_GLOBAL = "CONSULTAR_HISTORIAL_GLOBAL"


_BASE_PRESTATARIO = frozenset({
    Permiso.RESERVAR_ITEM,
    Permiso.SOLICITAR_PRESTAMO,
    Permiso.RENOVAR_PRESTAMO,
    Permiso.CONSULTAR_HISTORIAL_PROPIO,
})

_MATRIZ = {
    RolUsuario.ESTUDIANTE: _BASE_PRESTATARIO,
    RolUsuario.DOCENTE: _BASE_PRESTATARIO,
    RolUsuario.ADMINISTRATIVO: _BASE_PRESTATARIO,
    RolUsuario.GESTOR_INVENTARIO: frozenset({
        Permiso.CONSULTAR_PRESTATARIOS,
        Permiso.REGISTRAR_ITEM_INVENTARIO,
        Permiso.ACTUALIZAR_ESTADO_ITEM,
        Permiso.CONFIRMAR_RESERVA,
        Permiso.REGISTRAR_ENTREGA_PRESTAMO,
        Permiso.REGISTRAR_DEVOLUCION_PRESTAMO,
        Permiso.GENERAR_SANCION_MANUAL,
        Permiso.CONSULTAR_HISTORIAL_GLOBAL,
    }),
    RolUsuario.ADMINISTRADOR_SISTEMA: frozenset(Permiso),
}


@dataclass
class ServicioAutorizacionRol:
    def permisosDe(self, rol: RolUsuario) -> Set[Permiso]:
        return set(_MATRIZ[RolUsuario(rol)])

    def permisosDeRoles(self, roles: Iterable[RolUsuario]) -> Set[Permiso]:
        resultado: Set[Permiso] = set()
        for rol in roles:
            resultado |= self.permisosDe(rol)
        return resultado

    def tienePermiso(self, rol: RolUsuario, permiso: Permiso) -> bool:
        return Permiso(permiso) in self.permisosDe(rol)

    def rolesTienenPermiso(self, roles: Iterable[RolUsuario], permiso: Permiso) -> bool:
        return Permiso(permiso) in self.permisosDeRoles(roles)


@dataclass
class PerfilEstudiante:
    codigoEstudiante: Optional[str] = None
    matriculaVigente: Optional[bool] = None
    politicaServicioId: Optional[PoliticaServicioId] = None


@dataclass
class PerfilDocente:
    codigoEmpleado: Optional[str] = None
    tipoContrato: Optional[str] = None
    vinculacionVigente: bool = True
    politicaServicioId: Optional[PoliticaServicioId] = None


@dataclass
class PerfilAdministrativo:
    codigoEmpleado: Optional[str] = None
    cargoAdministrativo: Optional[str] = None
    vinculacionVigente: bool = True
    politicaServicioId: Optional[PoliticaServicioId] = None


@dataclass
class PerfilGestorInventario:
    codigoEmpleado: Optional[str] = None
    areaResponsable: Optional[str] = None
    fechaAsignacion: Optional[date] = None


@dataclass
class PerfilAdministradorSistema:
    codigoEmpleado: Optional[str] = None
    fechaAsignacion: Optional[date] = None


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
        return any(self.tieneRol(r) for r in (RolUsuario.ESTUDIANTE, *_ROLES_PRESTATARIOS))

    def tieneVinculacionVigente(self) -> bool:
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

    def _perfilPrestatario(self, rol: RolUsuario):
        return {
            RolUsuario.ESTUDIANTE: self.perfilEstudiante,
            RolUsuario.DOCENTE: self.perfilDocente,
            RolUsuario.ADMINISTRATIVO: self.perfilAdministrativo,
        }.get(RolUsuario(rol))

    def rolesPrestatarios(self) -> List[RolUsuario]:
        return [
            rol for rol in (RolUsuario.ESTUDIANTE, *_ROLES_PRESTATARIOS)
            if self.tieneRol(rol) and self._perfilPrestatario(rol) is not None
        ]

    def vinculacionVigentePara(self, rol: RolUsuario) -> bool:
        perfil = self._perfilPrestatario(rol)
        if perfil is None:
            return False
        if RolUsuario(rol) == RolUsuario.ESTUDIANTE:
            return bool(perfil.matriculaVigente)
        return bool(perfil.vinculacionVigente)

    def politicaIdPara(self, rol: RolUsuario):
        perfil = self._perfilPrestatario(rol)
        return perfil.politicaServicioId if perfil is not None else None


class IUsuarioRepository(ABC):
    @abstractmethod
    def save(self, usuario: Usuario, password_hash: Optional[str] = None) -> Usuario: ...

    @abstractmethod
    def find_by_id(self, usuario_id: int) -> Optional[Usuario]: ...

    @abstractmethod
    def find_by_email(self, correo: str) -> Optional[Usuario]: ...

    @abstractmethod
    def password_hash_de(self, usuario_id: int) -> Optional[str]: ...

    @abstractmethod
    def listar(self, *, texto=None, rol=None, activo=None) -> List[Usuario]: ...

    @abstractmethod
    def contar_administradores_activos(self) -> int: ...

    @abstractmethod
    def nombres_de(self, usuario_ids) -> dict: ...

    @abstractmethod
    def bloquear(self, usuario_id: int) -> None: ...
