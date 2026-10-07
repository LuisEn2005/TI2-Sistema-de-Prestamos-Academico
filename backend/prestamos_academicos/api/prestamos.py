"""Rutas del contexto Préstamos. Requieren autenticación (RNF04)."""

from flask import Blueprint, g, jsonify

from ..dominio.identidad import Permiso
from .autenticacion import requiere_autenticacion, requiere_permiso, servicios
from .peticion import cuerpo_json, id_positivo

bp = Blueprint("prestamos", __name__, url_prefix="/api")


@bp.get("/prestamos")
@requiere_autenticacion
def listar():
    return jsonify(servicios().prestamos.listar(g.usuario))


@bp.post("/prestamos")
@requiere_permiso(Permiso.REGISTRAR_ENTREGA_PRESTAMO)
def prestar():
    datos = cuerpo_json()
    usuario_id = id_positivo(datos.get("usuario_id"), "usuario_id")
    item_id = id_positivo(datos.get("item_id"), "item_id")
    return jsonify(servicios().prestamos.registrar(usuario_id, item_id)), 201


@bp.post("/prestamos/<int:prestamo_id>/devolucion")
@requiere_permiso(Permiso.REGISTRAR_DEVOLUCION_PRESTAMO)
def devolver(prestamo_id):
    return jsonify(servicios().prestamos.devolver(prestamo_id))
