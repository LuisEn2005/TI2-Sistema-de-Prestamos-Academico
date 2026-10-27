"""Pruebas de la configuracion central y del archivo .env."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from prestamos_academicos.configuracion import cargar_configuracion


class ConfiguracionTest(unittest.TestCase):
    def test_carga_env_y_mantiene_datos_demo_desactivados_por_defecto(self):
        with TemporaryDirectory() as directorio:
            ruta = Path(directorio) / ".env"
            ruta.write_text(
                "DATABASE_URL=sqlite:///prueba.sqlite\n"
                "SECRET_KEY=desde-archivo\n"
                "ZONA_HORARIA=America/Bogota\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                config = cargar_configuracion(ruta_env=ruta)

        self.assertEqual(config.database_url, "sqlite:///prueba.sqlite")
        self.assertEqual(config.secret_key, "desde-archivo")
        self.assertEqual(config.zona_horaria, "America/Bogota")
        self.assertFalse(config.datos_demo)

    def test_argumentos_y_entorno_tienen_prioridad_sobre_env(self):
        with TemporaryDirectory() as directorio:
            ruta = Path(directorio) / ".env"
            ruta.write_text(
                "DATABASE_URL=sqlite:///archivo.sqlite\n"
                "SECRET_KEY=archivo\n"
                "DATOS_DEMO=false\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"SECRET_KEY": "entorno"}, clear=True):
                config = cargar_configuracion(
                    database_url="sqlite:///:memory:",
                    secret_key="explicita",
                    datos_demo=True,
                    ruta_env=ruta,
                )

        self.assertEqual(config.database_url, "sqlite:///:memory:")
        self.assertEqual(config.secret_key, "explicita")
        self.assertTrue(config.datos_demo)
