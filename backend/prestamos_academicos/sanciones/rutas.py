"""API de sanciones."""

from flask import Blueprint, g, jsonify

from .dominio import EstadoSancion
from ..compartido import ErrorAplicacion
from ..compartido import validacion as v
from ..compartido.autenticacion import requiere_autenticacion, requiere_permiso, servicios
from ..compartido.http import (
    cuerpo_json, entero_consulta, id_positivo, id_ruta, parametros_permitidos, texto_consulta)
from ..identidad import Permiso

bp = Blueprint("sanciones", __name__, url_prefix="/api")


@bp.get("/sanciones")
@requiere_autenticacion
def listar():
    parametros_permitidos("estado")
    estado = texto_consulta("estado", maximo=20)
    if estado is not None:
        try:
            estado = EstadoSancion(estado.upper()).value
        except ValueError:
            raise ErrorAplicacion("El estado debe ser ACTIVA o CERRADA.", 400)
    return jsonify(servicios().sanciones.listar(g.usuario, estado))


@bp.get("/sanciones/recursos")
@requiere_permiso(Permiso.GENERAR_SANCION_MANUAL)
def recursos():
    """Recursos devueltos dañados o perdidos que pueden vincularse a una sanción manual."""
    parametros_permitidos("usuario_id")
    usuario_id = entero_consulta("usuario_id", None, maximo=2**31 - 1)
    if usuario_id is None:
        raise ErrorAplicacion("Indique el usuario («usuario_id»).", 400)
    return jsonify(servicios().sanciones.recursos_sancionables(usuario_id))


@bp.post("/sanciones")
@requiere_permiso(Permiso.GENERAR_SANCION_MANUAL)
def registrar():
    datos = cuerpo_json()
    v.campos(datos, {"usuario_id", "prestamo_id", "item_id", "motivo", "dias", "monto"})
    sancion = servicios().sanciones.registrar_manual(
        g.usuario,
        usuario_id=id_positivo(datos.get("usuario_id"), "usuario_id"),
        prestamo_id=id_positivo(datos.get("prestamo_id"), "prestamo_id"),
        item_id=id_positivo(datos.get("item_id"), "item_id"),
        motivo=v.texto(datos, "motivo", maximo=300),
        dias=datos.get("dias"), monto=datos.get("monto"),
    )
    return jsonify(sancion), 201


@bp.post("/sanciones/<int:sancion_id>/cierre")
@requiere_permiso(Permiso.LEVANTAR_SANCION)
def cerrar(sancion_id):
    datos = cuerpo_json()
    v.campos(datos, {"resolucion"})
    return jsonify(servicios().sanciones.cerrar(
        id_ruta(sancion_id), v.texto(datos, "resolucion", maximo=300), g.usuario))
