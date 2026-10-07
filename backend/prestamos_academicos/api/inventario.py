"""Rutas del contexto Inventario. El catálogo es público (RNF04)."""

from flask import Blueprint, jsonify, request

from ..dominio.identidad import Permiso
from .autenticacion import requiere_permiso, servicios
from .peticion import cuerpo_json, entero_consulta
from .serializadores import item_a_json, tipo_a_json

bp = Blueprint("inventario", __name__, url_prefix="/api")


@bp.get("/items")
def listar_items():
    items, total, pagina, limite = servicios().inventario.buscar(
        texto=request.args.get("q") or None,
        tipo=request.args.get("tipo") or None,
        categoria=request.args.get("categoria") or None,
        estado=request.args.get("estado") or None,
        pagina=entero_consulta("pagina", 1),
        limite=entero_consulta("limite", 20),
    )
    return jsonify({
        "items": [item_a_json(i) for i in items],
        "total": total, "pagina": pagina, "limite": limite,
    })


@bp.get("/items/tipos")
def listar_tipos():
    return jsonify([tipo_a_json(t) for t in servicios().inventario.listar_tipos()])


@bp.get("/items/categorias")
def listar_categorias():
    return jsonify(servicios().inventario.categorias())


@bp.get("/items/<int:item_id>")
def obtener_item(item_id):
    return jsonify(item_a_json(servicios().inventario.obtener(item_id)))


@bp.post("/items")
@requiere_permiso(Permiso.REGISTRAR_ITEM_INVENTARIO)
def registrar_item():
    return jsonify(item_a_json(servicios().inventario.registrar_item(cuerpo_json()))), 201


@bp.patch("/items/<int:item_id>")
@requiere_permiso(Permiso.REGISTRAR_ITEM_INVENTARIO)
def actualizar_item(item_id):
    return jsonify(item_a_json(servicios().inventario.actualizar_item(item_id, cuerpo_json())))


@bp.post("/items/<int:item_id>/estado")
@requiere_permiso(Permiso.ACTUALIZAR_ESTADO_ITEM)
def cambiar_estado(item_id):
    item = servicios().inventario.cambiar_estado(item_id, cuerpo_json().get("estado"))
    return jsonify(item_a_json(item))
