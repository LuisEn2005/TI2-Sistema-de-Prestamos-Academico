"""Factoría de la aplicación Flask."""

from flask import Flask

from .infraestructura.persistencia.base import Base
from .infraestructura.persistencia.conexion import crear_fabrica_sesiones
from .infraestructura.persistencia.datos_demo import cargar_datos_demo
from .infraestructura.persistencia import modelos  # registra las tablas en Base


def create_app(database_url=None):
    app = Flask(__name__)
    motor, fabrica_sesiones = crear_fabrica_sesiones(database_url)
    Base.metadata.create_all(motor)
    cargar_datos_demo(fabrica_sesiones)
    app.extensions["fabrica_sesiones"] = fabrica_sesiones

    from .api.mvp import bp as mvp_bp
    from .api.salud import bp as salud_bp

    app.register_blueprint(mvp_bp)
    app.register_blueprint(salud_bp)
    return app
