"""Repositorios SQLAlchemy de políticas normalizadas y modalidades."""

from sqlalchemy import delete, func, select

from .dominio import IModalidadRepository, IPoliticaRepository
from ..base_datos import mapeadores
from ..base_datos.modelos import (
    ModalidadDB, PoliticaRolDB, PoliticaServicioDB, PoliticaTipoRecursoDB,
)


class SqlAlchemyPoliticaRepository(IPoliticaRepository):
    def __init__(self, sesion):
        self.sesion = sesion

    def _a_dominio(self, fila):
        if fila is None:
            return None
        politica = mapeadores.politica_a_dominio(fila)
        regla = self.sesion.get(PoliticaRolDB, fila.rol_aplicable)
        if regla:
            politica.maxItemsSimultaneos = regla.max_items_simultaneos
            politica.diasSancionPorDiaAtraso = regla.dias_sancion_por_dia_atraso
        politica.modalidadNombre = self.sesion.scalar(
            select(ModalidadDB.nombre).where(ModalidadDB.id == fila.modalidad_id))
        politica.tiposRecursoPermitidos = list(self.sesion.scalars(
            select(PoliticaTipoRecursoDB.tipo_recurso_codigo)
            .where(PoliticaTipoRecursoDB.politica_servicio_id == fila.id)
            .order_by(PoliticaTipoRecursoDB.tipo_recurso_codigo)))
        return politica

    def save(self, politica):
        fila = self.sesion.get(PoliticaServicioDB, politica.id.valor) if politica.id else None
        fila = fila or PoliticaServicioDB()
        fila.rol_aplicable = politica.rolAplicable.value
        fila.modalidad_id = politica.modalidadId.valor
        fila.dias_prestamo = politica.diasPrestamo
        regla = self.sesion.get(PoliticaRolDB, politica.rolAplicable.value)
        if regla is None:
            regla = PoliticaRolDB(rol=politica.rolAplicable.value)
        regla.max_items_simultaneos = politica.maxItemsSimultaneos
        regla.dias_sancion_por_dia_atraso = politica.diasSancionPorDiaAtraso
        self.sesion.add(regla)
        self.sesion.add(fila)
        self.sesion.flush()
        self.sesion.execute(delete(PoliticaTipoRecursoDB).where(
            PoliticaTipoRecursoDB.politica_servicio_id == fila.id))
        for tipo in politica.tiposPermitidos():
            self.sesion.add(PoliticaTipoRecursoDB(
                politica_servicio_id=fila.id, tipo_recurso_codigo=tipo))
        self.sesion.flush()
        return self._a_dominio(fila)

    def find_by_rol_y_modalidad(self, rol, modalidad_id):
        fila = self.sesion.scalar(
            select(PoliticaServicioDB).where(
                PoliticaServicioDB.rol_aplicable == rol.value,
                PoliticaServicioDB.modalidad_id == modalidad_id,
            )
        )
        return self._a_dominio(fila)

    def listar_por_rol(self, rol):
        filas = self.sesion.scalars(select(PoliticaServicioDB).where(
            PoliticaServicioDB.rol_aplicable == rol.value).order_by(
                PoliticaServicioDB.modalidad_id))
        return [self._a_dominio(fila) for fila in filas]

    def find_by_id(self, politica_id):
        fila = self.sesion.get(PoliticaServicioDB, politica_id)
        return self._a_dominio(fila)

    def listar(self):
        filas = self.sesion.scalars(
            select(PoliticaServicioDB).order_by(PoliticaServicioDB.id)
        )
        return [self._a_dominio(fila) for fila in filas]

    def actualizar_regla_rol(self, rol, *, max_items=None, dias_sancion=None):
        fila = self.sesion.get(PoliticaRolDB, rol.value)
        if fila is None:
            return None
        if max_items is not None:
            fila.max_items_simultaneos = max_items
        if dias_sancion is not None:
            fila.dias_sancion_por_dia_atraso = dias_sancion
        self.sesion.flush()
        return fila

    def listar_reglas_rol(self):
        return list(self.sesion.scalars(select(PoliticaRolDB).order_by(PoliticaRolDB.rol)))


class SqlAlchemyModalidadRepository(IModalidadRepository):
    def __init__(self, sesion):
        self.sesion = sesion

    def save(self, modalidad):
        fila = self.sesion.get(ModalidadDB, modalidad.id.valor) if modalidad.id else None
        fila = fila or ModalidadDB()
        fila.nombre = modalidad.nombre
        fila.activo = bool(modalidad.activo)
        self.sesion.add(fila)
        self.sesion.flush()
        return mapeadores.modalidad_a_dominio(fila)

    def find_by_id(self, modalidad_id):
        fila = self.sesion.get(ModalidadDB, modalidad_id)
        return fila and mapeadores.modalidad_a_dominio(fila)

    def find_by_nombre(self, nombre):
        fila = self.sesion.scalar(
            select(ModalidadDB).where(
                func.lower(ModalidadDB.nombre) == nombre.strip().lower()
            )
        )
        return fila and mapeadores.modalidad_a_dominio(fila)

    def listar(self):
        filas = self.sesion.scalars(select(ModalidadDB).order_by(ModalidadDB.id))
        return [mapeadores.modalidad_a_dominio(fila) for fila in filas]
