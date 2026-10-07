"""Autenticación por token firmado (Bearer) y decoradores de autorización."""

import time
from functools import wraps

from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from ..aplicacion.errores import ErrorAplicacion, NoAutenticado, SinPermiso

DURACION_TOKEN_SEGUNDOS = 8 * 3600


class EmisorTokens:
    def __init__(self, clave_secreta, duracion=DURACION_TOKEN_SEGUNDOS):
        self._serializador = URLSafeTimedSerializer(clave_secreta, salt="prestamos-auth")
        self.duracion = duracion

    def emitir(self, usuario):
        return self._serializador.dumps({
            "uid": usuario.id.valor, "version_sesion": usuario.versionSesion,
        })

    def verificar(self, token):
        try:
            datos = self._serializador.loads(token, max_age=self.duracion)
            usuario_id = datos["uid"]
            version = datos["version_sesion"]
            if type(usuario_id) is not int or type(version) is not int:
                return None
            return usuario_id, version
        except (BadSignature, SignatureExpired, KeyError, TypeError):
            return None


class LimitadorIntentos:
    """Frena la fuerza bruta de contraseñas (en memoria; por proceso)."""

    def __init__(self, maximo=5, ventana=300):
        self.maximo, self.ventana = maximo, ventana
        self._fallos = {}

    def _vigentes(self, clave):
        limite = time.monotonic() - self.ventana
        self._fallos[clave] = [t for t in self._fallos.get(clave, []) if t > limite]
        return self._fallos[clave]

    def verificar(self, clave):
        if len(self._vigentes(clave)) >= self.maximo:
            raise ErrorAplicacion(
                "Demasiados intentos fallidos. Espere unos minutos e inténtelo de nuevo.", 429)

    def registrar_fallo(self, clave):
        self._vigentes(clave).append(time.monotonic())

    def limpiar(self, clave):
        self._fallos.pop(clave, None)


def servicios():
    return current_app.extensions["servicios"]


def _token_de_la_peticion():
    cabecera = request.headers.get("Authorization", "")
    esquema, _, token = cabecera.partition(" ")
    return token.strip() if esquema.lower() == "bearer" and token.strip() else None


def requiere_autenticacion(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        token = _token_de_la_peticion()
        sesion = servicios().tokens.verificar(token) if token else None
        usuario = servicios().identidad.usuario_de_sesion(*sesion) if sesion else None
        if usuario is None:
            raise NoAutenticado("Inicie sesión para continuar.")
        g.usuario = usuario
        return vista(*args, **kwargs)

    return envoltura


def requiere_permiso(permiso):
    def decorador(vista):
        @wraps(vista)
        @requiere_autenticacion
        def envoltura(*args, **kwargs):
            if permiso not in servicios().identidad.permisos_de(g.usuario):
                raise SinPermiso()
            return vista(*args, **kwargs)

        return envoltura

    return decorador
