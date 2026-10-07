"""Motor y sesiones de SQLAlchemy."""

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker


def _activar_claves_foraneas_sqlite(motor):
    @event.listens_for(motor, "connect")
    def _pragma(conexion, _registro):
        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def crear_fabrica_sesiones(database_url=None):
    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        ruta = Path(__file__).resolve().parents[3] / "instance" / "prestamos.sqlite"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{ruta}"

    motor = create_engine(url)
    if motor.dialect.name == "sqlite":
        _activar_claves_foraneas_sqlite(motor)
    return motor, sessionmaker(bind=motor, expire_on_commit=False)
