"""Modelos ORM de SQLAlchemy (ModelosORM).

Son independientes de las clases del dominio: DomainMapper convierte entre ambos.
Los roles de un usuario se deducen de los perfiles que tiene (patrón Party/Role).
"""

from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint, text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def _ahora():
    return datetime.now(timezone.utc)


class PoliticaServicioDB(Base):
    __tablename__ = "politicas_servicio"
    __table_args__ = (
        CheckConstraint("max_items_simultaneos > 0", name="ck_politica_max_positivo"),
        CheckConstraint("dias_prestamo_default > 0", name="ck_politica_dias_positivo"),
        CheckConstraint("dias_gracia_reserva >= 0", name="ck_politica_gracia_no_negativa"),
        CheckConstraint("length(trim(tipos_recurso_permitidos)) > 0",
                        name="ck_politica_tipos_no_vacios"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rol_aplicable: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    max_items_simultaneos: Mapped[int] = mapped_column(Integer, nullable=False)
    dias_prestamo_default: Mapped[int] = mapped_column(Integer, nullable=False)
    dias_gracia_reserva: Mapped[int] = mapped_column(Integer, nullable=False)
    tipos_recurso_permitidos: Mapped[str] = mapped_column(String(200), nullable=False)


class UsuarioDB(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint("length(trim(nombre)) > 0", name="ck_usuario_nombre_no_vacio"),
        CheckConstraint("correo = lower(trim(correo))", name="ck_usuario_correo_canonico"),
        CheckConstraint("length(trim(correo)) > 0", name="ck_usuario_correo_no_vacio"),
        CheckConstraint("version_sesion >= 0", name="ck_usuario_version_sesion_no_negativa"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    correo: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    # NULL = sin acceso al sistema hasta que un gestor asigne una contraseña.
    password_hash: Mapped[str | None] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version_sesion: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tiene_sancion_activa_cache: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_ahora
    )


class PerfilEstudianteDB(Base):
    __tablename__ = "perfiles_estudiante"
    __table_args__ = (CheckConstraint(
        "length(trim(codigo_estudiante)) > 0", name="ck_estudiante_codigo_no_vacio"),)

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
    __table_args__ = (
        CheckConstraint("length(trim(codigo_empleado)) > 0", name="ck_docente_codigo_no_vacio"),
        CheckConstraint("length(trim(tipo_contrato)) > 0", name="ck_docente_contrato_no_vacio"),
    )

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
    __table_args__ = (
        CheckConstraint("length(trim(codigo_empleado)) > 0",
                        name="ck_administrativo_codigo_no_vacio"),
        CheckConstraint("length(trim(cargo_administrativo)) > 0",
                        name="ck_administrativo_cargo_no_vacio"),
    )

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
    __table_args__ = (
        CheckConstraint("length(trim(codigo_empleado)) > 0", name="ck_gestor_codigo_no_vacio"),
        CheckConstraint("length(trim(area_responsable)) > 0", name="ck_gestor_area_no_vacia"),
    )

    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    codigo_empleado: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    area_responsable: Mapped[str] = mapped_column(String(80), nullable=False)
    fecha_asignacion: Mapped[date] = mapped_column(Date, nullable=False)


class PerfilAdministradorSistemaDB(Base):
    __tablename__ = "perfiles_administrador_sistema"
    __table_args__ = (CheckConstraint(
        "length(trim(codigo_empleado)) > 0", name="ck_admin_sistema_codigo_no_vacio"),)

    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    codigo_empleado: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    fecha_asignacion: Mapped[date] = mapped_column(Date, nullable=False)


class ItemDB(Base):
    """Catálogo común. Los atributos propios de cada tipo van en `atributos` (JSON),
    de modo que un tipo nuevo no requiere cambiar el esquema (RNF06)."""

    __tablename__ = "items"
    __table_args__ = (
        Index("ix_items_tipo_estado", "tipo", "estado"),
        Index("ix_items_categoria", "categoria"),
        CheckConstraint("codigo = upper(trim(codigo))", name="ck_item_codigo_canonico"),
        CheckConstraint("length(trim(codigo)) > 0", name="ck_item_codigo_no_vacio"),
        CheckConstraint("length(trim(nombre)) > 0", name="ck_item_nombre_no_vacio"),
        CheckConstraint("length(trim(categoria)) > 0", name="ck_item_categoria_no_vacia"),
        CheckConstraint("length(trim(tipo)) > 0", name="ck_item_tipo_no_vacio"),
        CheckConstraint(
            "estado IN ('DISPONIBLE','PRESTADO','RESERVADO','EN_MANTENIMIENTO',"
            "'DADO_DE_BAJA','EXTRAVIADO')", name="ck_item_estado_valido"),
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


class ModalidadDB(Base):
    """Forma de préstamo (en sala o externa) con su propio plazo en días (RF10)."""

    __tablename__ = "modalidades"
    __table_args__ = (
        CheckConstraint("length(trim(nombre)) > 0", name="ck_modalidad_nombre_no_vacio"),
        CheckConstraint("dias_plazo_default > 0", name="ck_modalidad_dias_positivo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    dias_plazo_default: Mapped[int] = mapped_column(Integer, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PrestamoDB(Base):
    """Cabecera del préstamo. La modalidad se guarda como copia (snapshot): cambiar la
    configuración después no altera los préstamos ya registrados. Los campos de
    modalidad, rol y fecha límite son NULL solo en préstamos anteriores al Sprint 3."""

    __tablename__ = "prestamos"
    __table_args__ = (
        CheckConstraint(
            "fecha_devolucion IS NULL OR fecha_devolucion >= fecha_prestamo",
            name="ck_prestamo_fechas_ordenadas"),
        CheckConstraint(
            "modalidad_dias_plazo IS NULL OR modalidad_dias_plazo > 0",
            name="ck_prestamo_plazo_positivo"),
        CheckConstraint(
            "dias_plazo_aplicado IS NULL OR dias_plazo_aplicado > 0",
            name="ck_prestamo_plazo_aplicado_positivo"),
        CheckConstraint(
            "rol_solicitante IS NULL OR rol_solicitante IN "
            "('ESTUDIANTE','DOCENTE','ADMINISTRATIVO')", name="ck_prestamo_rol_valido"),
        Index("ix_prestamos_usuario", "usuario_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    rol_solicitante: Mapped[str | None] = mapped_column(String(30))
    modalidad_id: Mapped[int | None] = mapped_column(ForeignKey("modalidades.id"))
    modalidad_nombre: Mapped[str | None] = mapped_column(String(60))
    modalidad_dias_plazo: Mapped[int | None] = mapped_column(Integer)
    dias_plazo_aplicado: Mapped[int | None] = mapped_column(Integer)
    fecha_prestamo: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_ahora
    )
    fecha_devolucion_esperada: Mapped[date | None] = mapped_column(Date)
    fecha_devolucion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DetallePrestamoDB(Base):
    """Un ítem dentro de un préstamo. `activo` es verdadero mientras el ítem no vuelve:
    un índice único parcial impide que un ítem esté en dos préstamos activos (RN3)."""

    __tablename__ = "detalles_prestamo"
    __table_args__ = (
        UniqueConstraint("prestamo_id", "item_id", name="uq_detalle_prestamo_item"),
        CheckConstraint(
            "condicion IS NULL OR condicion IN ('BUEN_ESTADO','DANADO','PERDIDO')",
            name="ck_detalle_condicion_valida"),
        Index("ix_detalles_prestamo", "prestamo_id"),
        Index("ux_detalles_item_activo", "item_id", unique=True,
              sqlite_where=text("activo"), postgresql_where=text("activo")),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prestamo_id: Mapped[int] = mapped_column(
        ForeignKey("prestamos.id", ondelete="CASCADE"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    condicion: Mapped[str | None] = mapped_column(String(20))
    observacion: Mapped[str | None] = mapped_column(String(300))
