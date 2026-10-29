"""Rutas del contexto Configuración (consulta de políticas por perfil y modalidades)."""

from flask import Blueprint, jsonify

from ..compartido import validacion as v
from ..compartido.autenticacion import requiere_autenticacion, requiere_permiso, servicios
from ..compartido.http import cuerpo_json, id_ruta
from ..identidad import Permiso

bp = Blueprint("configuracion", __name__, url_prefix="/api")


def modalidad_a_json(modalidad):
    return {
        "id": modalidad.id.valor,
        "nombre": modalidad.nombre,
        "activo": modalidad.activo,
    }


def politica_a_json(politica):
    return {
        "id": politica.id.valor,
        "rol": politica.rolAplicable.value,
        "modalidad_id": politica.modalidadId.valor,
        "modalidad": politica.modalidadNombre,
        "max_items_simultaneos": politica.maxItemsSimultaneos,
        "dias_prestamo": politica.diasPrestamo,
        "dias_sancion_por_dia_atraso": politica.diasSancionPorDiaAtraso,
        "tipos_recurso_permitidos": politica.tiposPermitidos(),
    }


@bp.get("/politicas")
@requiere_autenticacion
def listar_politicas():
    return jsonify([politica_a_json(p) for p in servicios().configuracion.listar_politicas()])


@bp.get("/modalidades")
@requiere_autenticacion
def listar_modalidades():
    return jsonify([modalidad_a_json(m) for m in servicios().configuracion.listar_modalidades()])


@bp.patch("/politicas/<int:politica_id>")
@requiere_permiso(Permiso.CONFIGURAR_POLITICAS)
def actualizar_politica(politica_id):
    return jsonify(politica_a_json(servicios().configuracion.actualizar_politica(
        id_ruta(politica_id), cuerpo_json())))


@bp.patch("/modalidades/<int:modalidad_id>")
@requiere_permiso(Permiso.CONFIGURAR_POLITICAS)
def actualizar_modalidad(modalidad_id):
    datos = cuerpo_json()
    v.campos(datos, {"activo"})
    return jsonify(modalidad_a_json(servicios().configuracion.actualizar_modalidad(
        id_ruta(modalidad_id), v.booleano(datos, "activo"))))
