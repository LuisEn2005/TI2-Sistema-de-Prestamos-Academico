"""Factoría de la aplicación Flask."""

import logging
import secrets
from types import SimpleNamespace

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .configuracion import cargar_configuracion
from .compartido import ErrorAplicacion, ErrorDominio
from .compartido.autenticacion import EmisorTokens, LimitadorIntentos
from .compartido.reloj import Reloj
from .configuracion_servicio.servicio import ConfiguracionApplicationService
from .identidad.servicio import IdentidadApplicationService
from .inventario.servicio import InventarioApplicationService
from .prestamos.servicio import PrestamoApplicationService
from .reservas.servicio import ReservaApplicationService
from .sanciones.servicio import SancionApplicationService
from .base_datos.conexion import crear_fabrica_sesiones
from .base_datos.datos_demo import preparar_datos
from .base_datos.aplicar_migraciones import aplicar_migraciones
from .base_datos.unidad_trabajo import SqlAlchemyUnitOfWork

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

    reloj_aplicacion = reloj or Reloj(config.zona_horaria)
    identidad = IdentidadApplicationService(fabrica_uow, reloj_aplicacion)
    app.extensions["servicios"] = SimpleNamespace(
        identidad=identidad,
        inventario=InventarioApplicationService(fabrica_uow),
        prestamos=PrestamoApplicationService(
            fabrica_uow, identidad, reloj_aplicacion),
        reservas=ReservaApplicationService(
            fabrica_uow, identidad, reloj_aplicacion),
        sanciones=SancionApplicationService(
            fabrica_uow, identidad, reloj_aplicacion),
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

    from .configuracion_servicio import rutas as rutas_configuracion
    from .identidad import rutas as rutas_identidad
    from .inventario import rutas as rutas_inventario
    from .prestamos import rutas as rutas_prestamos
    from .reservas import rutas as rutas_reservas
    from .sanciones import rutas as rutas_sanciones
    for modulo in (
            rutas_identidad, rutas_inventario, rutas_prestamos, rutas_reservas,
            rutas_configuracion, rutas_sanciones):
        app.register_blueprint(modulo.bp)

    @app.get("/api/salud")
    def salud():
        return {"estado": "ok"}

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
