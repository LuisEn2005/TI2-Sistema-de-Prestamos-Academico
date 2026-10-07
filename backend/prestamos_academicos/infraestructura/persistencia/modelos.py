"""Modelos ORM de SQLAlchemy (ModelosORM).

Son independientes de las clases del dominio: DomainMapper convierte entre ambos.
Los roles de un usuario se deducen de los perfiles que tiene (patrón Party/Role).
"""

from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def _ahora():
    return datetime.now(timezone.utc)


class PoliticaServicioDB(Base):
    __tablename__ = "politicas_servicio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rol_aplicable: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    max_items_simultaneos: Mapped[int] = mapped_column(Integer, nullable=False)
    dias_prestamo_default: Mapped[int] = mapped_column(Integer, nullable=False)
    dias_gracia_reserva: Mapped[int] = mapped_column(Integer, nullable=False)
    tipos_recurso_permitidos: Mapped[str] = mapped_column(String(200), nullable=False)


class UsuarioDB(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    correo: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    # NULL = sin acceso al sistema hasta que un gestor asigne una contraseña.
    password_hash: Mapped[str | None] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    tiene_sancion_activa_cache: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_ahora
    )


class PerfilEstudianteDB(Base):
    __tablename__ = "perfiles_estudiante"

    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    codigo_estudiante: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    matricula_vigente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    politica_servicio_id: Mapped[int] = mapped_column(
        ForeignKey("politicas_servicio.id"), nullable=False
    )


class PerfilDocenteDB(Base):
    __tablename__ = "perfiles_docente"

    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    codigo_empleado: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    tipo_contrato: Mapped[str] = mapped_column(String(60), nullable=False)
    vinculacion_vigente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    politica_servicio_id: Mapped[int] = mapped_column(
        ForeignKey("politicas_servicio.id"), nullable=False
    )


class PerfilAdministrativoDB(Base):
    __tablename__ = "perfiles_administrativo"

    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    codigo_empleado: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    cargo_administrativo: Mapped[str] = mapped_column(String(80), nullable=False)
    vinculacion_vigente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    politica_servicio_id: Mapped[int] = mapped_column(
        ForeignKey("politicas_servicio.id"), nullable=False
    )


class PerfilGestorInventarioDB(Base):
    __tablename__ = "perfiles_gestor_inventario"

    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    codigo_empleado: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    area_responsable: Mapped[str] = mapped_column(String(80), nullable=False)
    fecha_asignacion: Mapped[date] = mapped_column(Date, nullable=False)


class ItemDB(Base):
    """Catálogo común. Los atributos propios de cada tipo van en `atributos` (JSON),
    de modo que un tipo nuevo no requiere cambiar el esquema (RNF06)."""

    __tablename__ = "items"
    __table_args__ = (
        Index("ix_items_tipo_estado", "tipo", "estado"),
        Index("ix_items_categoria", "categoria"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    categoria: Mapped[str] = mapped_column(String(80), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="DISPONIBLE")
    atributos: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    texto_busqueda: Mapped[str] = mapped_column(Text, nullable=False, default="")
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_ahora
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_ahora, onupdate=_ahora
    )


class PrestamoDB(Base):
    __tablename__ = "prestamos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False)
    fecha_prestamo: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_ahora
    )
    fecha_devolucion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
