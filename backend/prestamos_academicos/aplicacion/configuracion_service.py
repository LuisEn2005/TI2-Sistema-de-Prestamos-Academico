"""Casos de uso del contexto Configuración (Sprint 2: consulta y valores base)."""

from ..configuracion_servicio import Modalidad, PoliticaServicio
from ..compartido import RolUsuario

# Políticas iniciales por perfil (RF03). El gestor no presta para sí mismo.
POLITICAS_BASE = {
    RolUsuario.ESTUDIANTE: dict(max=3, dias=7, gracia=2, tipos="LIBRO,EQUIPO,MATERIAL"),
    RolUsuario.DOCENTE: dict(max=5, dias=15, gracia=3, tipos="LIBRO,EQUIPO,MATERIAL,MOBILIARIO"),
    RolUsuario.ADMINISTRATIVO: dict(max=5, dias=15, gracia=3,
                                    tipos="LIBRO,EQUIPO,MATERIAL,MOBILIARIO"),
}

# Modalidades iniciales (RF10). El plazo de la modalidad es un tope: el plazo efectivo es el
# menor entre este y los días de la política del perfil (RN2). Pasan a ser editables en el Sprint 5.
MODALIDAD_IN_SITU = "In situ (en sala)"
MODALIDAD_EXTERNA = "Externa (a domicilio)"
MODALIDADES_BASE = ((MODALIDAD_IN_SITU, 1), (MODALIDAD_EXTERNA, 15))


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

    def asegurar_modalidades_base(self):
        with self._uow() as uow:
            for nombre, dias in MODALIDADES_BASE:
                if uow.modalidades.find_by_nombre(nombre) is None:
                    uow.modalidades.save(Modalidad(nombre=nombre, diasPlazoDefault=dias, activo=True))
            uow.commit()

    def listar_modalidades(self):
        with self._uow() as uow:
            return uow.modalidades.listar()

    def listar_politicas(self):
        with self._uow() as uow:
            return uow.politicas.listar()
