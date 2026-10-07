"""Factoría de la aplicación Flask."""

import logging
import os
import secrets
from types import SimpleNamespace

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .api.autenticacion import EmisorTokens, LimitadorIntentos
from .aplicacion.configuracion_service import ConfiguracionApplicationService
from .aplicacion.errores import ErrorAplicacion
from .aplicacion.identidad_service import IdentidadApplicationService
from .aplicacion.inventario_service import InventarioApplicationService
from .aplicacion.prestamo_service import PrestamoApplicationService
from .dominio.errores import ErrorDominio
from .infraestructura.persistencia.conexion import crear_fabrica_sesiones
from .infraestructura.persistencia.datos_demo import preparar_datos
from .infraestructura.persistencia.migraciones import aplicar_migraciones
from .infraestructura.persistencia.unidad_trabajo import SqlAlchemyUnitOfWork

log = logging.getLogger(__name__)


def _bandera(valor, defecto):
    if valor is None:
        return defecto
    return str(valor).strip().lower() not in ("0", "false", "no", "")


def create_app(database_url=None, *, datos_demo=None, secret_key=None):
    app = Flask(__name__)

    clave = secret_key or os.environ.get("SECRET_KEY")
    if not clave:
        clave = secrets.token_hex(32)
        log.warning("SECRET_KEY no definida: se usa una clave temporal; las sesiones "
                    "se invalidarán al reiniciar.")
    app.config["SECRET_KEY"] = clave

    motor, fabrica_sesiones = crear_fabrica_sesiones(database_url)
    aplicar_migraciones(motor)
    app.extensions["fabrica_sesiones"] = fabrica_sesiones

    def fabrica_uow():
        return SqlAlchemyUnitOfWork(fabrica_sesiones)

    identidad = IdentidadApplicationService(fabrica_uow)
    app.extensions["servicios"] = SimpleNamespace(
        identidad=identidad,
        inventario=InventarioApplicationService(fabrica_uow),
        prestamos=PrestamoApplicationService(fabrica_uow, identidad),
        configuracion=ConfiguracionApplicationService(fabrica_uow),
        tokens=EmisorTokens(clave),
        limitador=LimitadorIntentos(),
    )

    preparar_datos(
        fabrica_sesiones,
        datos_demo=_bandera(
            datos_demo if datos_demo is not None else os.environ.get("DATOS_DEMO"), False),
        admin_correo=os.environ.get("ADMIN_CORREO"),
        admin_password=os.environ.get("ADMIN_PASSWORD"),
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
