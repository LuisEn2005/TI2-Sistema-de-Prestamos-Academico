"""Entorno de Alembic. Sirve tanto para la CLI como para la ejecución desde la app."""

import os

from alembic import context
from sqlalchemy import create_engine

from prestamos_academicos.infraestructura.persistencia import modelos  # noqa: F401
from prestamos_academicos.infraestructura.persistencia.base import Base

config = context.config
target_metadata = Base.metadata


def _ejecutar(conexion):
    context.configure(
        connection=conexion,
        target_metadata=target_metadata,
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    conexion = config.attributes.get("connection")
    if conexion is not None:
        _ejecutar(conexion)
        return
    url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError("Defina DATABASE_URL para ejecutar las migraciones.")
    motor = create_engine(url)
    with motor.connect() as conexion:
        if motor.dialect.name == "sqlite":
            conexion.exec_driver_sql("PRAGMA foreign_keys=OFF")
            conexion.commit()
        _ejecutar(conexion)
        conexion.commit()


run_migrations_online()
