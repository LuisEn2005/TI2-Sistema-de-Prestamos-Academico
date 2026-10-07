from sqlalchemy import select

from ....dominio.prestamos import IPrestamoRepository
from .. import mapeador
from ..modelos import PrestamoDB


class SqlAlchemyPrestamoRepository(IPrestamoRepository):
    def __init__(self, sesion):
        self.sesion = sesion

    def save(self, prestamo):
        fila = self.sesion.get(PrestamoDB, prestamo.id.valor) if prestamo.id else None
        if fila is None:
            fila = PrestamoDB(
                usuario_id=prestamo.usuarioId.valor,
                item_id=prestamo.detalles[0].itemId.valor,
            )
            self.sesion.add(fila)
        fila.fecha_devolucion = prestamo.fechaDevolucionReal
        self.sesion.flush()
        return mapeador.prestamo_a_dominio(fila)

    def find_by_id(self, prestamo_id):
        fila = self.sesion.get(PrestamoDB, prestamo_id)
        return fila and mapeador.prestamo_a_dominio(fila)

    def find_activos(self):
        filas = self.sesion.scalars(
            select(PrestamoDB).where(PrestamoDB.fecha_devolucion.is_(None))
            .order_by(PrestamoDB.id.desc()))
        return [mapeador.prestamo_a_dominio(f) for f in filas]

    def listar(self, usuario_id=None):
        consulta = select(PrestamoDB).order_by(PrestamoDB.id.desc())
        if usuario_id is not None:
            consulta = consulta.where(PrestamoDB.usuario_id == usuario_id)
        return [mapeador.prestamo_a_dominio(f) for f in self.sesion.scalars(consulta)]
