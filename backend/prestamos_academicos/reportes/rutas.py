"""API de reportes PDF de acciones. Requieren autenticación (RNF04)."""

from datetime import date

from flask import Blueprint, Response, g

from .pdf import generar_pdf
from ..compartido import ErrorAplicacion
from ..compartido.autenticacion import requiere_autenticacion, requiere_permiso, servicios
from ..compartido.http import id_ruta, parametros_permitidos, texto_consulta
from ..identidad import Permiso

bp = Blueprint("reportes", __name__, url_prefix="/api")

MAX_DIAS_REPORTE = 90


def _rango():
    parametros_permitidos("desde", "hasta")
    desde_texto = texto_consulta("desde", maximo=10)
    hasta_texto = texto_consulta("hasta", maximo=10)
    if not desde_texto or not hasta_texto:
        raise ErrorAplicacion("Indique «desde» y «hasta» con formato AAAA-MM-DD.", 400)
    try:
        desde = date.fromisoformat(desde_texto)
        hasta = date.fromisoformat(hasta_texto)
    except ValueError:
        raise ErrorAplicacion("Las fechas deben usar el formato AAAA-MM-DD.", 400)
    if hasta < desde:
        raise ErrorAplicacion("«hasta» no puede ser anterior a «desde».", 400)
    if (hasta - desde).days > MAX_DIAS_REPORTE:
        raise ErrorAplicacion(
            f"El rango del reporte no puede superar {MAX_DIAS_REPORTE} días.", 400)
    return desde, hasta


def _pdf(datos, nombre):
    return Response(generar_pdf(datos), mimetype="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


@bp.get("/reportes/usuario/<int:usuario_id>")
@requiere_autenticacion
def reporte_usuario(usuario_id):
    desde, hasta = _rango()
    datos = servicios().reportes.datos_usuario(
        g.usuario, id_ruta(usuario_id), desde, hasta)
    return _pdf(datos, f"reporte-usuario-{usuario_id}-{desde}-a-{hasta}.pdf")


@bp.get("/reportes/item/<int:item_id>")
@requiere_permiso(Permiso.CONSULTAR_HISTORIAL_GLOBAL)
def reporte_item(item_id):
    desde, hasta = _rango()
    datos = servicios().reportes.datos_item(
        g.usuario, id_ruta(item_id), desde, hasta)
    return _pdf(datos, f"reporte-item-{item_id}-{desde}-a-{hasta}.pdf")
