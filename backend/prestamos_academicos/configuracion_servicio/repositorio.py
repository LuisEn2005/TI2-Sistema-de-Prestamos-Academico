"""Repositorios SQLAlchemy de politicas y modalidades."""

from sqlalchemy import func, select

from .dominio import IModalidadRepository, IPoliticaRepository
from ..base_datos import mapeadores
from ..base_datos.modelos import ModalidadDB, PoliticaServicioDB


class SqlAlchemyPoliticaRepository(IPoliticaRepository):
    def __init__(self, sesion):
        self.sesion = sesion

    def save(self, politica):
        fila = self.sesion.get(PoliticaServicioDB, politica.id.valor) if politica.id else None
        fila = fila or PoliticaServicioDB()
        fila.rol_aplicable = politica.rolAplicable.value
        fila.max_items_simultaneos = politica.maxItemsSimultaneos
        fila.dias_prestamo_default = politica.diasPrestamoDefault
        fila.dias_gracia_reserva = politica.diasGraciaReserva
        fila.tipos_recurso_permitidos = politica.tiposRecursoPermitidos
        self.sesion.add(fila)
        self.sesion.flush()
        return mapeadores.politica_a_dominio(fila)

    def find_by_rol(self, rol):
        fila = self.sesion.scalar(
            select(PoliticaServicioDB).where(
                PoliticaServicioDB.rol_aplicable == rol.value
            )
        )
        return fila and mapeadores.politica_a_dominio(fila)

    def find_by_id(self, politica_id):
        fila = self.sesion.get(PoliticaServicioDB, politica_id)
        return fila and mapeadores.politica_a_dominio(fila)

    def listar(self):
        filas = self.sesion.scalars(
            select(PoliticaServicioDB).order_by(PoliticaServicioDB.id)
        )
        return [mapeadores.politica_a_dominio(fila) for fila in filas]


class SqlAlchemyModalidadRepository(IModalidadRepository):
    def __init__(self, sesion):
        self.sesion = sesion

    def save(self, modalidad):
        fila = self.sesion.get(ModalidadDB, modalidad.id.valor) if modalidad.id else None
        fila = fila or ModalidadDB()
        fila.nombre = modalidad.nombre
        fila.dias_plazo_default = modalidad.diasPlazoDefault
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
