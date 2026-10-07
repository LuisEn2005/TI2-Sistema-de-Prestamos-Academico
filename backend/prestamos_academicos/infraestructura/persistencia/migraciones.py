"""Ejecución programática de las migraciones de Alembic al iniciar la aplicación."""

from pathlib import Path

from alembic import command
from alembic.config import Config

DIRECTORIO = Path(__file__).resolve().parents[1] / "migraciones"


def configuracion_alembic():
    cfg = Config()
    cfg.set_main_option("script_location", str(DIRECTORIO))
    return cfg


def aplicar_migraciones(motor):
    cfg = configuracion_alembic()
    es_sqlite = motor.dialect.name == "sqlite"
    with motor.connect() as conexion:
        if es_sqlite:
            # Alembic recrea tablas en SQLite: las claves foráneas se reactivan después.
            conexion.exec_driver_sql("PRAGMA foreign_keys=OFF")
            conexion.commit()
        cfg.attributes["connection"] = conexion
        command.upgrade(cfg, "head")
        conexion.commit()
        if es_sqlite:
            conexion.exec_driver_sql("PRAGMA foreign_keys=ON")
            conexion.commit()
