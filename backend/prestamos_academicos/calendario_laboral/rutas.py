"""API del calendario laboral y disponibilidad."""

from datetime import date

from flask import Blueprint, g, jsonify

from ..compartido import ErrorAplicacion
from ..compartido import validacion as v
from ..compartido.autenticacion import requiere_autenticacion, requiere_permiso, servicios
from ..compartido.http import cuerpo_json, entero_consulta, id_ruta, parametros_permitidos, texto_consulta
from ..identidad import Permiso

bp = Blueprint("calendario_laboral", __name__, url_prefix="/api")


def _fecha_consulta(nombre):
    valor = texto_consulta(nombre, maximo=10)
    if valor is None:
        raise ErrorAplicacion(f"El parámetro «{nombre}» es obligatorio.", 400)
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise ErrorAplicacion(f"«{nombre}» debe usar AAAA-MM-DD.", 400)


def _fecha_cuerpo(datos, nombre):
    valor = v.texto(datos, nombre, maximo=10)
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise ErrorAplicacion(f"«{nombre}» debe usar AAAA-MM-DD.", 400)


@bp.get("/calendario/hoy")
def fecha_actual():
    """Fecha institucional; evita que el navegador aplique otra zona horaria."""
    return jsonify({"fecha": servicios().calendario.reloj.hoy().isoformat()})


@bp.get("/items/<int:item_id>/calendario")
def calendario_publico(item_id):
    parametros_permitidos("desde", "hasta")
    return jsonify(servicios().calendario.calendario_item(
        id_ruta(item_id), _fecha_consulta("desde"), _fecha_consulta("hasta")))


@bp.get("/reservas/calendario")
@requiere_permiso(Permiso.CONFIRMAR_RESERVA)
def solicitudes_calendario():
    parametros_permitidos("item_id", "desde", "hasta")
    item_id = entero_consulta("item_id", None, maximo=9_223_372_036_854_775_807)
    if item_id is None:
        raise ErrorAplicacion("El parámetro «item_id» es obligatorio.", 400)
    return jsonify(servicios().calendario.solicitudes_item(
        item_id,
        _fecha_consulta("desde"), _fecha_consulta("hasta")))


@bp.get("/dias-no-laborables")
@requiere_autenticacion
def listar_cierres():
    parametros_permitidos("desde", "hasta")
    desde = texto_consulta("desde", maximo=10)
    hasta = texto_consulta("hasta", maximo=10)
    try:
        return jsonify(servicios().calendario.listar_cierres(
            date.fromisoformat(desde) if desde else None,
            date.fromisoformat(hasta) if hasta else None))
    except ValueError:
        raise ErrorAplicacion("Las fechas deben usar AAAA-MM-DD.", 400)


@bp.post("/dias-no-laborables")
@requiere_permiso(Permiso.CONFIGURAR_POLITICAS)
def registrar_cierre():
    datos = cuerpo_json()
    v.campos(datos, {"fecha_inicio", "fecha_fin", "tipo", "motivo"})
    return jsonify(servicios().calendario.registrar_cierre(
        g.usuario, _fecha_cuerpo(datos, "fecha_inicio"),
        _fecha_cuerpo(datos, "fecha_fin"),
        v.texto(datos, "tipo", maximo=20).upper(),
        v.texto(datos, "motivo", maximo=200))), 201


@bp.patch("/dias-no-laborables/<int:cierre_id>")
@requiere_permiso(Permiso.CONFIGURAR_POLITICAS)
def actualizar_cierre(cierre_id):
    datos = cuerpo_json()
    v.campos(datos, {"activo", "fecha_inicio", "fecha_fin", "tipo", "motivo"})
    if not datos:
        raise ErrorAplicacion("Indique al menos un cambio.", 400)
    tipo = v.texto(datos, "tipo", obligatorio=False, maximo=20)
    return jsonify(servicios().calendario.actualizar_cierre(
        id_ruta(cierre_id), activo=v.booleano(datos, "activo"),
        inicio=v.fecha(datos, "fecha_inicio"), fin=v.fecha(datos, "fecha_fin"),
        tipo=tipo.upper() if tipo else None,
        motivo=v.texto(datos, "motivo", obligatorio=False, maximo=200)))
