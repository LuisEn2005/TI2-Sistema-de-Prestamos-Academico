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
    v.campos(datos, {"item_id", "fecha_reserva", "rol_solicitante"})
    fecha_texto = v.texto(datos, "fecha_reserva", maximo=10, etiqueta="fecha de reserva")
    try:
        fecha = date.fromisoformat(fecha_texto)
    except ValueError:
        raise ErrorAplicacion("«fecha_reserva» debe usar el formato AAAA-MM-DD.", 400)
    rol = datos.get("rol_solicitante")
    if rol is not None and not isinstance(rol, str):
        raise ErrorAplicacion("«rol_solicitante» debe ser texto.", 400)
    return jsonify(servicios().reservas.crear(
        g.usuario, id_positivo(datos.get("item_id"), "item_id"), fecha, rol)), 201


@bp.post("/reservas/<int:reserva_id>/confirmacion")
@requiere_permiso(Permiso.CONFIRMAR_RESERVA)
def confirmar(reserva_id):
    v.campos(cuerpo_json(), set())
    return jsonify(servicios().reservas.confirmar(id_ruta(reserva_id)))


@bp.post("/reservas/<int:reserva_id>/cancelacion")
@requiere_autenticacion
def cancelar(reserva_id):
    v.campos(cuerpo_json(), set())
    return jsonify(servicios().reservas.cancelar(g.usuario, id_ruta(reserva_id)))


@bp.post("/reservas/<int:reserva_id>/prestamo")
@requiere_permiso(Permiso.REGISTRAR_ENTREGA_PRESTAMO)
def convertir(reserva_id):
    datos = cuerpo_json()
    v.campos(datos, {"modalidad_id"})
    servicios().reservas.expirar_vencidas()
    return jsonify(servicios().prestamos.registrar_desde_reserva(
        id_ruta(reserva_id), id_positivo(datos.get("modalidad_id"), "modalidad_id"))), 201
