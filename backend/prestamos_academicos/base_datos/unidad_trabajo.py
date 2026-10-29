"""Unidad de trabajo: una sesion y una transaccion para todos los repositorios."""

from abc import ABC, abstractmethod

from ..configuracion_servicio.repositorio import (
    SqlAlchemyModalidadRepository, SqlAlchemyPoliticaRepository,
)
from ..identidad.repositorio import SqlAlchemyUsuarioRepository
from ..inventario.repositorio import SqlAlchemyItemRepository
from ..prestamos.repositorio import SqlAlchemyPrestamoRepository
from ..reservas.repositorio import SqlAlchemyReservaRepository
from ..sanciones.repositorio import SqlAlchemySancionRepository


class IUnitOfWork(ABC):
    usuarios = None
    items = None
    politicas = None
    modalidades = None
    prestamos = None
    reservas = None
    sanciones = None

    @abstractmethod
    def begin(self): ...

    @abstractmethod
    def commit(self): ...

    @abstractmethod
    def rollback(self): ...

    def __enter__(self):
        self.begin()
        return self

    def __exit__(self, tipo, valor, traza):
        self.rollback()
        return False


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self, fabrica_sesiones):
        self._fabrica = fabrica_sesiones
        self.sesion = None

    def begin(self):
        self.sesion = self._fabrica()
        self.usuarios = SqlAlchemyUsuarioRepository(self.sesion)
        self.items = SqlAlchemyItemRepository(self.sesion)
        self.politicas = SqlAlchemyPoliticaRepository(self.sesion)
        self.modalidades = SqlAlchemyModalidadRepository(self.sesion)
        self.prestamos = SqlAlchemyPrestamoRepository(self.sesion)
        self.reservas = SqlAlchemyReservaRepository(self.sesion)
        self.sanciones = SqlAlchemySancionRepository(self.sesion)

    def commit(self):
        self.sesion.commit()

    def rollback(self):
        if self.sesion is not None:
            try:
                self.sesion.rollback()
            finally:
                self.sesion.close()
                self.sesion = None
