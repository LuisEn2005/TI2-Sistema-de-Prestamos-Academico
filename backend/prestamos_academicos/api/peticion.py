"""Lectura y validación de parámetros de la petición HTTP."""

from flask import request

from ..aplicacion.errores import ErrorAplicacion

MAX_ID = 9_223_372_036_854_775_807


def cuerpo_json():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorAplicacion("Envíe un objeto JSON en el cuerpo de la petición.", 400)
    return datos


def entero_consulta(nombre, defecto, *, minimo=1, maximo=100):
    crudo = request.args.get(nombre)
    if crudo in (None, ""):
        return defecto
    try:
        valor = int(crudo)
    except ValueError:
        raise ErrorAplicacion(f"El parámetro «{nombre}» debe ser un entero.", 400)
    if valor < minimo or valor > maximo:
        raise ErrorAplicacion(
            f"El parámetro «{nombre}» debe estar entre {minimo} y {maximo}.", 400)
    return valor


def texto_consulta(nombre, *, maximo):
    crudo = request.args.get(nombre)
    if crudo in (None, ""):
        return None
    valor = crudo.strip()
    if len(valor) > maximo:
        raise ErrorAplicacion(
            f"El parámetro «{nombre}» admite hasta {maximo} caracteres.", 400)
    return valor or None


def parametros_permitidos(*nombres):
    desconocidos = set(request.args) - set(nombres)
    if desconocidos:
        lista = ", ".join(f"«{nombre}»" for nombre in sorted(desconocidos))
        raise ErrorAplicacion(f"Parámetros de consulta no admitidos: {lista}.", 400)


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
    if type(valor) is not int or valor < 1 or valor > MAX_ID:
        raise ErrorAplicacion(f"{nombre} debe ser un entero positivo.", 400)
    return valor


def id_ruta(valor, nombre="El identificador"):
    return id_positivo(valor, nombre)
