"""Utilidades de validación de datos de entrada (texto, booleanos, fechas)."""

from datetime import date

from .errores import ErrorAplicacion


def texto(datos, clave, *, obligatorio=True, maximo=120, etiqueta=None):
    etiqueta = etiqueta or clave
    valor = datos.get(clave)
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        if obligatorio:
            raise ErrorAplicacion(f"El campo «{etiqueta}» es obligatorio.", 400)
        return None
    if not isinstance(valor, str):
        raise ErrorAplicacion(f"El campo «{etiqueta}» debe ser texto.", 400)
    valor = valor.strip()
    if len(valor) > maximo:
        raise ErrorAplicacion(f"El campo «{etiqueta}» admite hasta {maximo} caracteres.", 400)
    return valor


def booleano(datos, clave, *, defecto=None):
    if clave not in datos or datos[clave] is None:
        return defecto
    if not isinstance(datos[clave], bool):
        raise ErrorAplicacion(f"El campo «{clave}» debe ser verdadero o falso.", 400)
    return datos[clave]


def fecha(datos, clave, *, defecto=None):
    valor = datos.get(clave)
    if valor is None or valor == "":
        return defecto
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        raise ErrorAplicacion(f"El campo «{clave}» debe tener formato AAAA-MM-DD.", 400)


def objeto(valor, nombre="el cuerpo"):
    if not isinstance(valor, dict):
        raise ErrorAplicacion(f"Se esperaba un objeto JSON en {nombre}.", 400)
    return valor
