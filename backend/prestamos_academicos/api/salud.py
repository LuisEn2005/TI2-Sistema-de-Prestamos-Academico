"""Ruta básica para comprobar que la API responde."""

from flask import Blueprint

bp = Blueprint("salud", __name__, url_prefix="/api")


@bp.get("/salud")
def salud():
    return {"estado": "ok"}
