"""Rutas del contexto Configuración (Sprint 2: consulta de políticas por perfil)."""

from flask import Blueprint, jsonify

from .autenticacion import requiere_autenticacion, servicios
from .serializadores import politica_a_json

bp = Blueprint("configuracion", __name__, url_prefix="/api")


@bp.get("/politicas")
@requiere_autenticacion
def listar_politicas():
    return jsonify([politica_a_json(p) for p in servicios().configuracion.listar_politicas()])
