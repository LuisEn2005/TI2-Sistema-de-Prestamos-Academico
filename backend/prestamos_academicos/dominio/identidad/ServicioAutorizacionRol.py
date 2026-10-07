"""
<<domain service>> ServicioAutorizacionRol
Encapsula la matriz rol -> permisos del modelo.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Set

from ..shared_kernel import RolUsuario
from .Permiso import Permiso

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
        """Unión de permisos: un usuario puede tener varios roles."""
        resultado: Set[Permiso] = set()
        for rol in roles:
            resultado |= self.permisosDe(rol)
        return resultado

    def tienePermiso(self, rol: RolUsuario, permiso: Permiso) -> bool:
        return Permiso(permiso) in self.permisosDe(rol)

    def rolesTienenPermiso(self, roles: Iterable[RolUsuario], permiso: Permiso) -> bool:
        return Permiso(permiso) in self.permisosDeRoles(roles)
