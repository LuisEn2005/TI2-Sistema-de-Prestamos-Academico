"""API REST de reservas."""

from datetime import date

from flask import Blueprint, g, jsonify

from .dominio import EstadoReserva
from ..compartido import ErrorAplicacion
from ..compartido import validacion as v
from ..compartido.autenticacion import requiere_autenticacion, requiere_permiso, servicios
from ..compartido.http import (
    cuerpo_json, entero_consulta, id_positivo, id_ruta, parametros_permitidos, texto_consulta,
)
from ..identidad import Permiso


bp = Blueprint("reservas", __name__, url_prefix="/api")


@bp.get("/reservas")
@requiere_autenticacion
def listar():
    parametros_permitidos("estado", "pagina", "limite")
    estado_texto = texto_consulta("estado", maximo=20)
    try:
        estado = EstadoReserva(estado_texto.upper()) if estado_texto else None
    except ValueError:
        raise ErrorAplicacion(
            "«estado» no corresponde a un estado de reserva válido.", 400)
    return jsonify(servicios().reservas.listar(
        g.usuario, estado=estado,
        pagina=entero_consulta("pagina", 1, maximo=100_000),
        limite=entero_consulta("limite", 20, maximo=100)))


@bp.post("/reservas")
@requiere_permiso(Permiso.RESERVAR_ITEM)
def crear():
    datos = cuerpo_json()
    v.campos(datos, {
        "item_id", "modalidad_id", "fecha_inicio", "fecha_fin",
        "fecha_reserva", "rol_solicitante"})
    inicio_texto = datos.get("fecha_inicio") or datos.get("fecha_reserva")
    fin_texto = datos.get("fecha_fin") or inicio_texto
    try:
        inicio = date.fromisoformat(inicio_texto)
        fin = date.fromisoformat(fin_texto)
    except (TypeError, ValueError):
        raise ErrorAplicacion("Las fechas deben usar el formato AAAA-MM-DD.", 400)
    rol = datos.get("rol_solicitante")
    if rol is not None and not isinstance(rol, str):
        raise ErrorAplicacion("«rol_solicitante» debe ser texto.", 400)
    modalidad_id = datos.get("modalidad_id")
    if modalidad_id is not None:
        modalidad_id = id_positivo(modalidad_id, "modalidad_id")
    return jsonify(servicios().reservas.crear(
        g.usuario, id_positivo(datos.get("item_id"), "item_id"), inicio, fin,
        modalidad_id, rol)), 201


@bp.post("/reservas/<int:reserva_id>/confirmacion")
@requiere_permiso(Permiso.CONFIRMAR_RESERVA)
def confirmar(reserva_id):
    datos = cuerpo_json()
    v.campos(datos, {"fecha_fin"})
    fecha_fin = datos.get("fecha_fin")
    if fecha_fin is not None:
        try:
            fecha_fin = date.fromisoformat(fecha_fin)
        except (TypeError, ValueError):
            raise ErrorAplicacion("«fecha_fin» debe usar AAAA-MM-DD.", 400)
    return jsonify(servicios().reservas.confirmar(
        g.usuario, id_ruta(reserva_id), fecha_fin))


@bp.post("/reservas/<int:reserva_id>/rechazo")
@requiere_permiso(Permiso.CONFIRMAR_RESERVA)
def rechazar(reserva_id):
    datos = cuerpo_json()
    v.campos(datos, {"motivo"})
    return jsonify(servicios().reservas.rechazar(
        id_ruta(reserva_id),
        v.texto(datos, "motivo", obligatorio=False, maximo=300)
        or "Solicitud rechazada por el gestor."))


@bp.post("/reservas/<int:reserva_id>/cancelacion")
@requiere_autenticacion
def cancelar(reserva_id):
    v.campos(cuerpo_json(), set())
    return jsonify(servicios().reservas.cancelar(g.usuario, id_ruta(reserva_id)))


@bp.post("/reservas/<int:reserva_id>/prestamo")
@requiere_permiso(Permiso.REGISTRAR_ENTREGA_PRESTAMO)
def convertir(reserva_id):
    datos = cuerpo_json()
    v.campos(datos, {"modalidad_id", "fecha_fin"})
    fecha_fin = datos.get("fecha_fin")
    if fecha_fin is not None:
        try:
            fecha_fin = date.fromisoformat(fecha_fin)
        except (TypeError, ValueError):
            raise ErrorAplicacion("«fecha_fin» debe usar AAAA-MM-DD.", 400)
    servicios().reservas.expirar_vencidas()
    return jsonify(servicios().prestamos.registrar_desde_reserva(
        id_ruta(reserva_id),
        id_positivo(datos.get("modalidad_id"), "modalidad_id")
        if datos.get("modalidad_id") is not None else None,
        fecha_fin)), 201
