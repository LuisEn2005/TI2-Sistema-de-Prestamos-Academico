"""Errores de negocio del dominio. No dependen de ningún framework."""


class ErrorDominio(Exception):
    """Una regla de negocio no se cumple."""


class TransicionInvalida(ErrorDominio):
    """El cambio de estado solicitado no está permitido."""
