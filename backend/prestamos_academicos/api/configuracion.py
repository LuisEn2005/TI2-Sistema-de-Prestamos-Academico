"""Rutas del contexto Configuración (consulta de políticas por perfil y modalidades)."""

from flask import Blueprint, jsonify

from .autenticacion import requiere_autenticacion, servicios
from .serializadores import modalidad_a_json, politica_a_json

bp = Blueprint("configuracion", __name__, url_prefix="/api")


@bp.get("/politicas")
@requiere_autenticacion
def listar_politicas():
    return jsonify([politica_a_json(p) for p in servicios().configuracion.listar_politicas()])


@bp.get("/modalidades")
@requiere_autenticacion
def listar_modalidades():
    return jsonify([modalidad_a_json(m) for m in servicios().configuracion.listar_modalidades()])
