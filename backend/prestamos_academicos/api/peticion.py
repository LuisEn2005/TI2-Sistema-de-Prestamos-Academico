"""Lectura y validación de parámetros de la petición HTTP."""

from flask import request

from ..aplicacion.errores import ErrorAplicacion


def cuerpo_json():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorAplicacion("Envíe un objeto JSON en el cuerpo de la petición.", 400)
    return datos


def entero_consulta(nombre, defecto):
    crudo = request.args.get(nombre)
    if crudo in (None, ""):
        return defecto
    try:
        return int(crudo)
    except ValueError:
        raise ErrorAplicacion(f"El parámetro «{nombre}» debe ser un entero.", 400)


def booleano_consulta(nombre):
    crudo = request.args.get(nombre)
    if crudo in (None, ""):
        return None
    if crudo.lower() in ("true", "1", "si", "sí"):
        return True
    if crudo.lower() in ("false", "0", "no"):
        return False
    raise ErrorAplicacion(f"El parámetro «{nombre}» debe ser true o false.", 400)


def id_positivo(valor, nombre):
    if type(valor) is not int or valor < 1:
        raise ErrorAplicacion(f"{nombre} debe ser un entero positivo.", 400)
    return valor
