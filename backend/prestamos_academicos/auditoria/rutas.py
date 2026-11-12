"""API REST del historial unificado (RF17). Requiere autenticación (RNF04)."""

from datetime import date

from flask import Blueprint, g, jsonify

from .dominio import TipoEvento
from ..compartido import ErrorAplicacion
from ..compartido.autenticacion import requiere_autenticacion, servicios
from ..compartido.http import (
    entero_consulta, id_positivo, parametros_permitidos, texto_consulta,
)

bp = Blueprint("historial", __name__, url_prefix="/api")


def _fecha(nombre):
    texto = texto_consulta(nombre, maximo=10)
    if texto is None:
        return None
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise ErrorAplicacion(f"«{nombre}» debe usar el formato AAAA-MM-DD.", 400)


def _id_opcional(nombre):
    texto = texto_consulta(nombre, maximo=12)
    if texto is None:
        return None
    try:
        return id_positivo(int(texto), nombre)
    except ValueError:
        raise ErrorAplicacion(f"«{nombre}» debe ser un entero positivo.", 400)


@bp.get("/historial")
@requiere_autenticacion
def consultar():
    parametros_permitidos(
        "tipo", "estado", "desde", "hasta", "usuario_id", "item_id", "pagina", "limite")
    tipo = None
    tipo_texto = texto_consulta("tipo", maximo=12)
    if tipo_texto:
        try:
            tipo = TipoEvento(tipo_texto.upper())
        except ValueError:
            raise ErrorAplicacion(
                "«tipo» debe ser PRESTAMO, RESERVA o SANCION.", 400)
    return jsonify(servicios().historial.consultar(
        g.usuario, tipo=tipo, estado=texto_consulta("estado", maximo=20),
        desde=_fecha("desde"), hasta=_fecha("hasta"),
        usuario_id=_id_opcional("usuario_id"), item_id=_id_opcional("item_id"),
        pagina=entero_consulta("pagina", 1, maximo=100_000),
        limite=entero_consulta("limite", 20, maximo=100)))
