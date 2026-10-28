"""Rutas del contexto Identidad: sesión y gestión de usuarios (RF01-RF03)."""

from flask import Blueprint, g, jsonify, request

from .dominio import Permiso
from ..compartido import validacion as v
from ..compartido import NoAutenticado
from ..compartido.autenticacion import (
    requiere_autenticacion, requiere_permiso, servicios,
)
from ..compartido.http import (
    booleano_consulta, cuerpo_json, id_ruta, parametros_permitidos, texto_consulta,
)

bp = Blueprint("identidad", __name__, url_prefix="/api")


def _fecha(valor):
    return valor.isoformat() if valor else None


def usuario_a_json(usuario, permisos=None):
    perfiles = {}
    if usuario.perfilEstudiante:
        p = usuario.perfilEstudiante
        perfiles["ESTUDIANTE"] = {
            "codigo_estudiante": p.codigoEstudiante,
            "matricula_vigente": p.matriculaVigente,
        }
    if usuario.perfilDocente:
        p = usuario.perfilDocente
        perfiles["DOCENTE"] = {
            "codigo_empleado": p.codigoEmpleado,
            "tipo_contrato": p.tipoContrato,
            "vinculacion_vigente": p.vinculacionVigente,
        }
    if usuario.perfilAdministrativo:
        p = usuario.perfilAdministrativo
        perfiles["ADMINISTRATIVO"] = {
            "codigo_empleado": p.codigoEmpleado,
            "cargo_administrativo": p.cargoAdministrativo,
            "vinculacion_vigente": p.vinculacionVigente,
        }
    if usuario.perfilGestorInventario:
        p = usuario.perfilGestorInventario
        perfiles["GESTOR_INVENTARIO"] = {
            "codigo_empleado": p.codigoEmpleado,
            "area_responsable": p.areaResponsable,
            "fecha_asignacion": _fecha(p.fechaAsignacion),
        }
    if usuario.perfilAdministradorSistema:
        p = usuario.perfilAdministradorSistema
        perfiles["ADMINISTRADOR_SISTEMA"] = {
            "codigo_empleado": p.codigoEmpleado,
            "fecha_asignacion": _fecha(p.fechaAsignacion),
        }
    datos = {
        "id": usuario.id.valor,
        "nombre": usuario.nombre,
        "correo": usuario.correoElectronico,
        "activo": usuario.activo,
        "roles": [rol.value for rol in usuario.roles],
        "perfiles": perfiles,
        "tiene_sancion_activa": usuario.tieneSancionActiva(),
        "habilitado": usuario.estaHabilitado(),
        "motivo_no_habilitado": usuario.motivoNoHabilitado(),
    }
    if permisos is not None:
        datos["permisos"] = sorted(Permiso(permiso).value for permiso in permisos)
    return datos


def prestatario_a_json(usuario):
    return {
        "id": usuario.id.valor,
        "nombre": usuario.nombre,
        "correo": usuario.correoElectronico,
    }


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
