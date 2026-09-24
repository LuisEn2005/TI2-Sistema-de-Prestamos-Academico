"""API JSON del recorrido mínimo del sistema."""

from flask import Blueprint, current_app, jsonify, request

from ..aplicacion.operaciones_mvp import (
    ErrorOperacion,
    devolver_prestamo,
    listar_prestamos,
    listar_recursos,
    listar_usuarios,
    registrar_prestamo,
)

bp = Blueprint("mvp", __name__, url_prefix="/api")


def _sesiones():
    return current_app.extensions["fabrica_sesiones"]


@bp.errorhandler(ErrorOperacion)
def error_operacion(error):
    return jsonify({"error": str(error)}), error.estado_http


@bp.get("/recursos")
def recursos():
    return jsonify(listar_recursos(_sesiones()))


@bp.get("/usuarios")
def usuarios():
    return jsonify(listar_usuarios(_sesiones()))


@bp.get("/prestamos")
def prestamos():
    return jsonify(listar_prestamos(_sesiones()))


@bp.post("/prestamos")
def prestar():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return {"error": "Envíe un objeto JSON con usuario_id y recurso_id."}, 400

    usuario_id = datos.get("usuario_id")
    recurso_id = datos.get("recurso_id")
    if any(type(valor) is not int or valor < 1 for valor in (usuario_id, recurso_id)):
        return {"error": "usuario_id y recurso_id deben ser enteros positivos."}, 400

    prestamo = registrar_prestamo(_sesiones(), usuario_id, recurso_id)
    return jsonify(prestamo), 201


@bp.post("/prestamos/<int:prestamo_id>/devolucion")
def devolver(prestamo_id):
    return jsonify(devolver_prestamo(_sesiones(), prestamo_id))
