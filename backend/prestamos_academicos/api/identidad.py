"""Rutas del contexto Identidad: sesión y gestión de usuarios (RF01-RF03)."""

from flask import Blueprint, g, jsonify, request

from ..dominio.identidad import Permiso
from ..aplicacion import validacion as v
from ..aplicacion.errores import NoAutenticado
from .autenticacion import (
    requiere_autenticacion, requiere_permiso, servicios,
)
from .peticion import (
    booleano_consulta, cuerpo_json, id_ruta, parametros_permitidos, texto_consulta,
)
from .serializadores import prestatario_a_json, usuario_a_json

bp = Blueprint("identidad", __name__, url_prefix="/api")


def _usuario_json(usuario):
    return usuario_a_json(usuario, servicios().identidad.permisos_de(usuario))


@bp.post("/auth/login")
def iniciar_sesion():
    datos = cuerpo_json()
    v.campos(datos, {"correo", "password"})
    clave = (request.remote_addr or "?", str(datos.get("correo", "")).strip().lower())
    limitador = servicios().limitador
    limitador.verificar(clave)
    try:
        usuario = servicios().identidad.autenticar(datos.get("correo"), datos.get("password"))
    except NoAutenticado:
        limitador.registrar_fallo(clave)
        raise
    limitador.limpiar(clave)
    return jsonify({
        "token": servicios().tokens.emitir(usuario),
        "usuario": _usuario_json(usuario),
    })


@bp.get("/auth/yo")
@requiere_autenticacion
def mi_perfil():
    return jsonify(_usuario_json(g.usuario))


@bp.post("/auth/cambiar-password")
@requiere_autenticacion
def cambiar_password():
    datos = cuerpo_json()
    v.campos(datos, {"password_actual", "password_nueva"})
    servicios().identidad.cambiar_password(
        g.usuario.id.valor, datos.get("password_actual"), datos.get("password_nueva"))
    return jsonify({"mensaje": "Contraseña actualizada."})


@bp.get("/usuarios")
@requiere_permiso(Permiso.GESTIONAR_USUARIOS_Y_ROLES)
def listar_usuarios():
    parametros_permitidos("q", "rol", "activo", "habilitado")
    usuarios = servicios().identidad.listar_usuarios(
        texto=texto_consulta("q", maximo=120),
        rol=texto_consulta("rol", maximo=30),
        activo=booleano_consulta("activo"),
        habilitado=booleano_consulta("habilitado"),
    )
    return jsonify([usuario_a_json(u) for u in usuarios])


@bp.get("/usuarios/<int:usuario_id>")
@requiere_permiso(Permiso.GESTIONAR_USUARIOS_Y_ROLES)
def obtener_usuario(usuario_id):
    return jsonify(usuario_a_json(servicios().identidad.obtener_usuario(id_ruta(usuario_id))))


@bp.get("/usuarios/prestatarios")
@requiere_permiso(Permiso.CONSULTAR_PRESTATARIOS)
def listar_prestatarios():
    parametros_permitidos("q")
    usuarios = servicios().identidad.listar_usuarios(
        texto=texto_consulta("q", maximo=120), habilitado=True)
    return jsonify([prestatario_a_json(u) for u in usuarios[:50]])


@bp.post("/usuarios")
@requiere_permiso(Permiso.GESTIONAR_USUARIOS_Y_ROLES)
def registrar_usuario():
    usuario = servicios().identidad.registrar_usuario(cuerpo_json())
    return jsonify(usuario_a_json(usuario)), 201


@bp.patch("/usuarios/<int:usuario_id>")
@requiere_permiso(Permiso.GESTIONAR_USUARIOS_Y_ROLES)
def actualizar_usuario(usuario_id):
    usuario = servicios().identidad.actualizar_usuario(
        id_ruta(usuario_id), cuerpo_json(), g.usuario)
    return jsonify(usuario_a_json(usuario))
