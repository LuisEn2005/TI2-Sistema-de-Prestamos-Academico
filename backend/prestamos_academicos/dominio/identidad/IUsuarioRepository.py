"""<<Repository Interface>> IUsuarioRepository (puerto del dominio)."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional

from .Usuario import Usuario


class IUsuarioRepository(ABC):
    @abstractmethod
    def save(self, usuario: Usuario, password_hash: Optional[str] = None) -> Usuario: ...

    @abstractmethod
    def find_by_id(self, usuario_id: int) -> Optional[Usuario]: ...

    @abstractmethod
    def find_by_email(self, correo: str) -> Optional[Usuario]: ...

    @abstractmethod
    def password_hash_de(self, usuario_id: int) -> Optional[str]: ...

    @abstractmethod
    def listar(self, *, texto=None, rol=None, activo=None) -> List[Usuario]: ...

    @abstractmethod
    def contar_administradores_activos(self) -> int: ...

    @abstractmethod
    def nombres_de(self, usuario_ids) -> dict:
        """Nombres por id en una sola consulta: {id: nombre}."""

    @abstractmethod
    def bloquear(self, usuario_id: int) -> None:
        """Serializa las operaciones concurrentes sobre un usuario (bloqueo de fila)."""
