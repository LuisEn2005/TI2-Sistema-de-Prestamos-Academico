from sqlalchemy import func, select

from ....configuracion_servicio import IModalidadRepository
from .. import mapeador
from ..modelos import ModalidadDB


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
        return mapeador.modalidad_a_dominio(fila)

    def find_by_id(self, modalidad_id):
        fila = self.sesion.get(ModalidadDB, modalidad_id)
        return fila and mapeador.modalidad_a_dominio(fila)

    def find_by_nombre(self, nombre):
        fila = self.sesion.scalar(
            select(ModalidadDB).where(func.lower(ModalidadDB.nombre) == nombre.strip().lower()))
        return fila and mapeador.modalidad_a_dominio(fila)

    def listar(self):
        filas = self.sesion.scalars(select(ModalidadDB).order_by(ModalidadDB.id))
        return [mapeador.modalidad_a_dominio(f) for f in filas]
