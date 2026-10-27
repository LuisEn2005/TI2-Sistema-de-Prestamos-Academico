"""Errores de negocio y aplicacion, independientes de Flask."""


class ErrorDominio(Exception):
    """Una regla de negocio no se cumple."""


class TransicionInvalida(ErrorDominio):
    """El cambio de estado solicitado no esta permitido."""


class ErrorAplicacion(Exception):
    """Error esperado de un caso de uso, con su estado HTTP sugerido."""

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
