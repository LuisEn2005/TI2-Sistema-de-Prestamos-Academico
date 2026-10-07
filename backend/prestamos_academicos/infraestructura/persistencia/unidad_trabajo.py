"""SqlAlchemyUnitOfWork: transacción única con acceso a los repositorios."""

from ...aplicacion.unidad_trabajo import IUnitOfWork
from .repositorios import (
    SqlAlchemyItemRepository, SqlAlchemyPoliticaRepository,
    SqlAlchemyPrestamoRepository, SqlAlchemyUsuarioRepository,
)


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self, fabrica_sesiones):
        self._fabrica = fabrica_sesiones
        self.sesion = None

    def begin(self):
        self.sesion = self._fabrica()
        self.usuarios = SqlAlchemyUsuarioRepository(self.sesion)
        self.items = SqlAlchemyItemRepository(self.sesion)
        self.politicas = SqlAlchemyPoliticaRepository(self.sesion)
        self.prestamos = SqlAlchemyPrestamoRepository(self.sesion)

    def commit(self):
        self.sesion.commit()

    def rollback(self):
        if self.sesion is not None:
            try:
                self.sesion.rollback()
            finally:
                self.sesion.close()
                self.sesion = None
