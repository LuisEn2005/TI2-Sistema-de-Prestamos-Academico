"""Rutas del contexto Préstamos. Requieren autenticación (RNF04)."""

from flask import Blueprint, g, jsonify

from ..identidad import Permiso
from ..compartido import ErrorAplicacion
from ..compartido import validacion as v
from .servicio import MAX_ITEMS_POR_PRESTAMO
from ..compartido.autenticacion import requiere_autenticacion, requiere_permiso, servicios
from ..compartido.http import (
    cuerpo_json, entero_consulta, id_positivo, id_ruta, parametros_permitidos, texto_consulta,
)

bp = Blueprint("prestamos", __name__, url_prefix="/api")
ESTADOS_LISTADO = ("activo", "vencido", "devuelto")


def _modalidad_y_rol(datos):
    modalidad_id = id_positivo(datos.get("modalidad_id"), "modalidad_id")
    rol = datos.get("rol_solicitante")
    if rol is not None and not isinstance(rol, str):
        raise ErrorAplicacion("«rol_solicitante» debe ser texto.", 400)
    return modalidad_id, rol


@bp.get("/prestamos")
@requiere_autenticacion
def listar():
    parametros_permitidos("estado", "pagina", "limite")
    estado = texto_consulta("estado", maximo=20)
    if estado is not None and estado not in ESTADOS_LISTADO:
        raise ErrorAplicacion(f"«estado» debe ser uno de: {', '.join(ESTADOS_LISTADO)}.", 400)
    return jsonify(servicios().prestamos.listar(
        g.usuario, estado=estado,
        pagina=entero_consulta("pagina", 1, maximo=100_000),
        limite=entero_consulta("limite", 20, maximo=100)))


@bp.get("/prestamos/condiciones")
@requiere_permiso(Permiso.REGISTRAR_ENTREGA_PRESTAMO)
def condiciones():
    """Plazo y cupo que aplicaría una entrega (misma lógica que POST /api/prestamos)."""
    from flask import request
    parametros_permitidos("usuario_id", "modalidad_id", "rol_solicitante")
    try:
        usuario_id = int(request.args.get("usuario_id", ""))
        modalidad_id = int(request.args.get("modalidad_id", ""))
    except ValueError:
        raise ErrorAplicacion("«usuario_id» y «modalidad_id» deben ser enteros.", 400)
    return jsonify(servicios().prestamos.condiciones(
        id_positivo(usuario_id, "usuario_id"), id_positivo(modalidad_id, "modalidad_id"),
        texto_consulta("rol_solicitante", maximo=30)))


@bp.get("/prestamos/<int:prestamo_id>")
@requiere_autenticacion
def detalle(prestamo_id):
    return jsonify(servicios().prestamos.obtener(g.usuario, id_ruta(prestamo_id)))


@bp.post("/prestamos")
@requiere_permiso(Permiso.REGISTRAR_ENTREGA_PRESTAMO)
def prestar():
    datos = cuerpo_json()
    v.campos(datos, {"usuario_id", "item_ids", "modalidad_id", "rol_solicitante"})
    usuario_id = id_positivo(datos.get("usuario_id"), "usuario_id")
    item_ids = datos.get("item_ids")
    if not isinstance(item_ids, list) or not item_ids:
        raise ErrorAplicacion("«item_ids» debe ser una lista con al menos un ítem.", 400)
    if len(item_ids) > MAX_ITEMS_POR_PRESTAMO:
        raise ErrorAplicacion(
            f"Un préstamo admite hasta {MAX_ITEMS_POR_PRESTAMO} ítems.", 400)
    item_ids = [id_positivo(i, "item_ids") for i in item_ids]
    if len(set(item_ids)) != len(item_ids):
        raise ErrorAplicacion("«item_ids» no puede repetir ítems.", 400)
    modalidad_id, rol = _modalidad_y_rol(datos)
    return jsonify(servicios().prestamos.registrar(usuario_id, item_ids, modalidad_id, rol)), 201


@bp.post("/prestamos/<int:prestamo_id>/devolucion")
@requiere_permiso(Permiso.REGISTRAR_DEVOLUCION_PRESTAMO)
def devolver(prestamo_id):
    datos = cuerpo_json()
    v.campos(datos, {"condiciones"})
    return jsonify(servicios().prestamos.devolver(id_ruta(prestamo_id), datos.get("condiciones")))
