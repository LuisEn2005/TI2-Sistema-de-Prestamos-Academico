"""Casos de uso del contexto Configuración (Sprint 2: consulta y valores base)."""

from .dominio import Modalidad, PoliticaServicio
from ..compartido import RolUsuario

# Políticas iniciales por perfil (RF03). El gestor no presta para sí mismo.
POLITICAS_BASE = {
    RolUsuario.ESTUDIANTE: dict(max=3, externa=7, gracia=2,
                                tipos=["LIBRO", "EQUIPO", "MATERIAL"]),
    RolUsuario.DOCENTE: dict(max=5, externa=15, gracia=3,
                             tipos=["LIBRO", "EQUIPO", "MATERIAL", "MOBILIARIO"]),
    RolUsuario.ADMINISTRATIVO: dict(max=5, externa=15, gracia=3,
                                    tipos=["LIBRO", "EQUIPO", "MATERIAL", "MOBILIARIO"]),
}

# Las modalidades son un catálogo. Los plazos se definen por rol y modalidad.
MODALIDAD_IN_SITU = "In situ (en sala)"
MODALIDAD_EXTERNA = "Externa (a domicilio)"
MODALIDADES_BASE = (MODALIDAD_IN_SITU, MODALIDAD_EXTERNA)


class ConfiguracionApplicationService:
    def __init__(self, fabrica_uow):
        self._uow = fabrica_uow

    def asegurar_politicas_base(self):
        with self._uow() as uow:
            modalidades = {m.nombre: m for m in uow.modalidades.listar()}
            for rol, p in POLITICAS_BASE.items():
                for nombre, dias in (
                        (MODALIDAD_IN_SITU, 1), (MODALIDAD_EXTERNA, p["externa"])):
                    modalidad = modalidades[nombre]
                    if uow.politicas.find_by_rol_y_modalidad(rol, modalidad.id.valor) is None:
                        uow.politicas.save(PoliticaServicio(
                            rolAplicable=rol, modalidadId=modalidad.id,
                            modalidadNombre=modalidad.nombre,
                            maxItemsSimultaneos=p["max"], diasPrestamo=dias,
                            diasGraciaReserva=p["gracia"],
                            tiposRecursoPermitidos=p["tipos"]))
            uow.commit()

    def asegurar_modalidades_base(self):
        with self._uow() as uow:
            for nombre in MODALIDADES_BASE:
                if uow.modalidades.find_by_nombre(nombre) is None:
                    uow.modalidades.save(Modalidad(nombre=nombre, activo=True))
            uow.commit()

    def listar_modalidades(self):
        with self._uow() as uow:
            return uow.modalidades.listar()

    def listar_politicas(self):
        with self._uow() as uow:
            return uow.politicas.listar()
