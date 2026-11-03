"""Rutas del contexto Inventario. El catálogo es público (RNF04)."""

from datetime import date

from flask import Blueprint, jsonify

from ..identidad import Permiso
from ..compartido.autenticacion import requiere_permiso, servicios
from ..compartido.http import (
    cuerpo_json, entero_consulta, id_ruta, parametros_permitidos, texto_consulta,
)
from ..compartido import ErrorAplicacion

bp = Blueprint("inventario", __name__, url_prefix="/api")


def item_a_json(item):
    return {
        "id": item.id.valor,
        "codigo": item.codigo,
        "nombre": item.nombre,
        "categoria": item.categoria,
        "tipo": item.TIPO,
        "estado": item.estado.value,
        "disponible": item.estaDisponible(),
        "atributos": {
            clave: valor for clave, valor in item.atributosEspecificos().items()
            if valor is not None
        },
    }


def tipo_a_json(tipo):
    return {
        "tipo": tipo.nombre,
        "etiqueta": tipo.etiqueta,
        "campos": [
            {
                "clave": campo.clave,
                "etiqueta": campo.etiqueta,
                "obligatorio": campo.obligatorio,
            }
            for campo in tipo.campos
        ],
    }


@bp.get("/items")
def listar_items():
    parametros_permitidos("q", "tipo", "categoria", "estado", "pagina", "limite")
    items, total, pagina, limite = servicios().inventario.buscar(
        texto=texto_consulta("q", maximo=120),
        tipo=texto_consulta("tipo", maximo=30),
        categoria=texto_consulta("categoria", maximo=80),
        estado=texto_consulta("estado", maximo=30),
        pagina=entero_consulta("pagina", 1, maximo=100_000),
        limite=entero_consulta("limite", 20, maximo=100),
    )
    return jsonify({
        "items": [item_a_json(i) for i in items],
        "total": total, "pagina": pagina, "limite": limite,
    })


@bp.get("/items/tipos")
def listar_tipos():
    return jsonify([tipo_a_json(t) for t in servicios().inventario.listar_tipos()])


@bp.get("/inventario")
@requiere_permiso(Permiso.REGISTRAR_ITEM_INVENTARIO)
def inventario_por_fecha():
    parametros_permitidos("fecha", "q", "tipo", "estado", "pagina", "limite")
    fecha_texto = texto_consulta("fecha", maximo=10)
    try:
        fecha = (date.fromisoformat(fecha_texto) if fecha_texto
                 else servicios().calendario.reloj.hoy())
    except ValueError:
        raise ErrorAplicacion("«fecha» debe usar AAAA-MM-DD.", 400)
    estado = texto_consulta("estado", maximo=30)
    validos = {"DISPONIBLE", "RESERVADO", "PRESTADO", "NO_DISPONIBLE"}
    if estado and estado not in validos:
        raise ErrorAplicacion(
            f"«estado» debe ser uno de: {', '.join(sorted(validos))}.", 400)
    return jsonify(servicios().calendario.inventario_fecha(
        fecha, texto=texto_consulta("q", maximo=120),
        tipo=texto_consulta("tipo", maximo=30), estado=estado,
        pagina=entero_consulta("pagina", 1, maximo=100_000),
        limite=entero_consulta("limite", 15, maximo=100)))


@bp.get("/items/categorias")
def listar_categorias():
    return jsonify(servicios().inventario.categorias())


@bp.get("/items/<int:item_id>")
def obtener_item(item_id):
    return jsonify(item_a_json(servicios().inventario.obtener(id_ruta(item_id))))


@bp.post("/items")
@requiere_permiso(Permiso.REGISTRAR_ITEM_INVENTARIO)
def registrar_item():
    return jsonify(item_a_json(servicios().inventario.registrar_item(cuerpo_json()))), 201


@bp.patch("/items/<int:item_id>")
@requiere_permiso(Permiso.REGISTRAR_ITEM_INVENTARIO)
def actualizar_item(item_id):
    return jsonify(item_a_json(
        servicios().inventario.actualizar_item(id_ruta(item_id), cuerpo_json())))


@bp.post("/items/<int:item_id>/estado")
@requiere_permiso(Permiso.ACTUALIZAR_ESTADO_ITEM)
def cambiar_estado(item_id):
    item = servicios().inventario.cambiar_estado(id_ruta(item_id), cuerpo_json())
    return jsonify(item_a_json(item))
