"""Errores de la capa de aplicación; la API los traduce a respuestas HTTP."""


class ErrorAplicacion(Exception):
    def __init__(self, mensaje, estado_http=400):
        super().__init__(mensaje)
        self.estado_http = estado_http


class NoAutenticado(ErrorAplicacion):
    def __init__(self, mensaje="Credenciales inválidas."):
        super().__init__(mensaje, 401)


class SinPermiso(ErrorAplicacion):
    def __init__(self, mensaje="No tiene permiso para esta operación."):
        super().__init__(mensaje, 403)


class NoEncontrado(ErrorAplicacion):
    def __init__(self, mensaje):
        super().__init__(mensaje, 404)


class Conflicto(ErrorAplicacion):
    def __init__(self, mensaje):
        super().__init__(mensaje, 409)
