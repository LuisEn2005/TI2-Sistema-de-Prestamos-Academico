"""Casos de uso del contexto Configuración (Sprint 2: consulta y valores base)."""

from .dominio import Modalidad, PoliticaServicio
from ..compartido import RolUsuario
from ..compartido import ErrorAplicacion, NoEncontrado
from ..compartido import validacion as v

# Políticas iniciales por perfil (RF03). El gestor no presta para sí mismo.
POLITICAS_BASE = {
    RolUsuario.ESTUDIANTE: dict(max=3, externa=7,
                                tipos=["LIBRO", "EQUIPO", "MATERIAL"]),
    RolUsuario.DOCENTE: dict(max=5, externa=14,
                             tipos=["LIBRO", "EQUIPO", "MATERIAL", "MOBILIARIO"]),
    RolUsuario.ADMINISTRATIVO: dict(max=5, externa=14,
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
                            diasSancionPorDiaAtraso=1,
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

    def listar_reglas_rol(self):
        with self._uow() as uow:
            return [{
                "rol": fila.rol,
                "max_items_simultaneos": fila.max_items_simultaneos,
                "dias_sancion_por_dia_atraso": fila.dias_sancion_por_dia_atraso,
            } for fila in uow.politicas.listar_reglas_rol()]

    @staticmethod
    def _entero(datos, clave, minimo, maximo):
        valor = datos.get(clave)
        if type(valor) is not int or not minimo <= valor <= maximo:
            raise ErrorAplicacion(
                f"«{clave}» debe estar entre {minimo} y {maximo}.", 400)
        return valor

    def actualizar_politica(self, politica_id, datos):
        datos = v.objeto(datos)
        v.campos(datos, {"dias_prestamo"})
        if not datos:
            raise ErrorAplicacion("Indique al menos una regla para actualizar.", 400)
        with self._uow() as uow:
            politica = uow.politicas.find_by_id(politica_id)
            if politica is None:
                raise NoEncontrado("La política no existe.")
            if "dias_prestamo" in datos:
                if politica.modalidadNombre == MODALIDAD_IN_SITU:
                    raise ErrorAplicacion(
                        "El préstamo in situ siempre termina al final del mismo día.", 422)
                politica.diasPrestamo = self._entero(datos, "dias_prestamo", 1, 365)
            guardada = uow.politicas.save(politica)
            uow.commit()
        return guardada

    def actualizar_regla_rol(self, rol_texto, datos):
        datos = v.objeto(datos)
        v.campos(datos, {"max_items_simultaneos", "dias_sancion_por_dia_atraso"})
        if not datos:
            raise ErrorAplicacion("Indique al menos una regla para actualizar.", 400)
        try:
            rol = RolUsuario(rol_texto.upper())
        except ValueError:
            raise ErrorAplicacion("El perfil indicado no tiene políticas de préstamo.", 400)
        if rol not in POLITICAS_BASE:
            raise ErrorAplicacion("El perfil indicado no tiene políticas de préstamo.", 400)
        maximo = (self._entero(datos, "max_items_simultaneos", 1, 50)
                  if "max_items_simultaneos" in datos else None)
        sancion = (self._entero(datos, "dias_sancion_por_dia_atraso", 1, 30)
                   if "dias_sancion_por_dia_atraso" in datos else None)
        with self._uow() as uow:
            guardada = uow.politicas.actualizar_regla_rol(
                rol, max_items=maximo, dias_sancion=sancion)
            if guardada is None:
                raise NoEncontrado("La política del perfil no existe.")
            vista = {
                "rol": guardada.rol,
                "max_items_simultaneos": guardada.max_items_simultaneos,
                "dias_sancion_por_dia_atraso": guardada.dias_sancion_por_dia_atraso,
            }
            uow.commit()
        return vista

    def actualizar_modalidad(self, modalidad_id, activo):
        if activo is None:
            raise ErrorAplicacion("«activo» es obligatorio.", 400)
        with self._uow() as uow:
            modalidad = uow.modalidades.find_by_id(modalidad_id)
            if modalidad is None:
                raise NoEncontrado("La modalidad no existe.")
            modalidad.activo = activo
            guardada = uow.modalidades.save(modalidad)
            uow.commit()
        return guardada
