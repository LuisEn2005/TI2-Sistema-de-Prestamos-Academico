"""Configuracion central de la aplicacion.

Los argumentos explicitos usados por pruebas tienen prioridad sobre el entorno. El
archivo ``.env`` de la raiz solo completa variables que el sistema operativo no
haya definido.
"""

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
RUTA_ENV = RAIZ_PROYECTO / ".env"
ZONA_POR_DEFECTO = "America/Lima"


def _bandera(valor, defecto=False):
    if valor is None:
        return defecto
    return str(valor).strip().lower() not in ("0", "false", "no", "")


@dataclass(frozen=True)
class Configuracion:
    database_url: str | None
    secret_key: str | None
    datos_demo: bool
    admin_correo: str | None
    admin_password: str | None
    zona_horaria: str


def cargar_configuracion(
    *, database_url=None, datos_demo=None, secret_key=None, ruta_env=RUTA_ENV,
):
    """Carga una configuracion predecible sin sobrescribir el entorno activo."""
    load_dotenv(dotenv_path=ruta_env, override=False)
    return Configuracion(
        database_url=database_url or os.environ.get("DATABASE_URL"),
        secret_key=secret_key or os.environ.get("SECRET_KEY"),
        datos_demo=_bandera(
            datos_demo if datos_demo is not None else os.environ.get("DATOS_DEMO"),
            False,
        ),
        admin_correo=os.environ.get("ADMIN_CORREO"),
        admin_password=os.environ.get("ADMIN_PASSWORD"),
        zona_horaria=os.environ.get("ZONA_HORARIA") or ZONA_POR_DEFECTO,
    )
