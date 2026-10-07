"""Casos de uso del contexto Configuración (Sprint 2: consulta y valores base)."""

from ..dominio.configuracion import PoliticaServicio
from ..dominio.shared_kernel import RolUsuario

# Políticas iniciales por perfil (RF03). El gestor no presta para sí mismo.
POLITICAS_BASE = {
    RolUsuario.ESTUDIANTE: dict(max=3, dias=7, gracia=2, tipos="LIBRO,EQUIPO,MATERIAL"),
    RolUsuario.DOCENTE: dict(max=5, dias=15, gracia=3, tipos="LIBRO,EQUIPO,MATERIAL,MOBILIARIO"),
    RolUsuario.ADMINISTRATIVO: dict(max=5, dias=15, gracia=3,
                                    tipos="LIBRO,EQUIPO,MATERIAL,MOBILIARIO"),
}


class ConfiguracionApplicationService:
    def __init__(self, fabrica_uow):
        self._uow = fabrica_uow

    def asegurar_politicas_base(self):
        with self._uow() as uow:
            for rol, p in POLITICAS_BASE.items():
                if uow.politicas.find_by_rol(rol) is None:
                    uow.politicas.save(PoliticaServicio(
                        rolAplicable=rol, maxItemsSimultaneos=p["max"],
                        diasPrestamoDefault=p["dias"], diasGraciaReserva=p["gracia"],
                        tiposRecursoPermitidos=p["tipos"]))
            uow.commit()

    def listar_politicas(self):
        with self._uow() as uow:
            return uow.politicas.listar()
