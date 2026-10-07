"""<<interface>> IUnitOfWork: define la transacción sin depender de la tecnología."""
from __future__ import annotations
from abc import ABC, abstractmethod


class IUnitOfWork(ABC):
    usuarios = None
    items = None
    politicas = None
    prestamos = None

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
        self.rollback()  # no-op si ya se confirmó
        return False
