"""Factoría de la aplicación Flask."""

import logging
import secrets
from types import SimpleNamespace

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .configuracion import cargar_configuracion
from .api.autenticacion import EmisorTokens, LimitadorIntentos
from .aplicacion.configuracion_service import ConfiguracionApplicationService
from .aplicacion.errores import ErrorAplicacion
from .aplicacion.identidad_service import IdentidadApplicationService
from .aplicacion.inventario_service import InventarioApplicationService
from .aplicacion.prestamo_service import PrestamoApplicationService
from .aplicacion.reloj import Reloj
from .compartido import ErrorDominio
from .infraestructura.persistencia.conexion import crear_fabrica_sesiones
from .infraestructura.persistencia.datos_demo import preparar_datos
from .infraestructura.persistencia.migraciones import aplicar_migraciones
from .infraestructura.persistencia.unidad_trabajo import SqlAlchemyUnitOfWork

log = logging.getLogger(__name__)


def create_app(database_url=None, *, datos_demo=None, secret_key=None, reloj=None):
    app = Flask(__name__)
    config = cargar_configuracion(
        database_url=database_url, datos_demo=datos_demo, secret_key=secret_key,
    )

    clave = config.secret_key
    if not clave:
        clave = secrets.token_hex(32)
        log.warning("SECRET_KEY no definida: se usa una clave temporal; las sesiones "
                    "se invalidarán al reiniciar.")
    app.config["SECRET_KEY"] = clave

    motor, fabrica_sesiones = crear_fabrica_sesiones(config.database_url)
    aplicar_migraciones(motor)
    app.extensions["fabrica_sesiones"] = fabrica_sesiones

    def fabrica_uow():
        return SqlAlchemyUnitOfWork(fabrica_sesiones)

    identidad = IdentidadApplicationService(fabrica_uow)
    app.extensions["servicios"] = SimpleNamespace(
        identidad=identidad,
        inventario=InventarioApplicationService(fabrica_uow),
        prestamos=PrestamoApplicationService(
            fabrica_uow, identidad, reloj or Reloj(config.zona_horaria)),
        configuracion=ConfiguracionApplicationService(fabrica_uow),
        tokens=EmisorTokens(clave),
        limitador=LimitadorIntentos(),
    )

    preparar_datos(
        fabrica_sesiones,
        datos_demo=config.datos_demo,
        admin_correo=config.admin_correo,
        admin_password=config.admin_password,
    )

    from .api import configuracion, identidad as api_identidad, inventario, prestamos, salud
    for modulo in (salud, api_identidad, inventario, prestamos, configuracion):
        app.register_blueprint(modulo.bp)

    @app.errorhandler(ErrorAplicacion)
    def error_aplicacion(error):
        return jsonify({"error": str(error)}), error.estado_http

    @app.errorhandler(ErrorDominio)
    def error_dominio(error):
        return jsonify({"error": str(error)}), 409

    @app.errorhandler(HTTPException)
    def error_http(error):
        return jsonify({"error": error.description}), error.code

    @app.errorhandler(Exception)
    def error_inesperado(error):
        log.exception("Error no controlado")
        return jsonify({"error": "Error interno del servidor."}), 500

    return app
