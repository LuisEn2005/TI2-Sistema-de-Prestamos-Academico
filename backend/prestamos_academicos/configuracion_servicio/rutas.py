"""Rutas del contexto Configuración (consulta de políticas por perfil y modalidades)."""

from flask import Blueprint, jsonify

from ..compartido.autenticacion import requiere_autenticacion, servicios

bp = Blueprint("configuracion", __name__, url_prefix="/api")


def modalidad_a_json(modalidad):
    return {
        "id": modalidad.id.valor,
        "nombre": modalidad.nombre,
        "dias_plazo_default": modalidad.diasPlazoDefault,
        "activo": modalidad.activo,
    }


def politica_a_json(politica):
    return {
        "id": politica.id.valor,
        "rol": politica.rolAplicable.value,
        "max_items_simultaneos": politica.maxItemsSimultaneos,
        "dias_prestamo_default": politica.diasPrestamoDefault,
        "dias_gracia_reserva": politica.diasGraciaReserva,
        "tipos_recurso_permitidos": [
            tipo for tipo in politica.tiposRecursoPermitidos.split(",") if tipo
        ],
    }


@bp.get("/politicas")
@requiere_autenticacion
def listar_politicas():
    return jsonify([politica_a_json(p) for p in servicios().configuracion.listar_politicas()])


@bp.get("/modalidades")
@requiere_autenticacion
def listar_modalidades():
    return jsonify([modalidad_a_json(m) for m in servicios().configuracion.listar_modalidades()])
