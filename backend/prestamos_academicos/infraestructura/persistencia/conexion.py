"""Motor y sesiones de SQLAlchemy para el prototipo."""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def crear_fabrica_sesiones(database_url=None):
    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        ruta = Path(__file__).resolve().parents[3] / "instance" / "prestamos.sqlite"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{ruta}"

    motor = create_engine(url)
    return motor, sessionmaker(bind=motor, expire_on_commit=False)
