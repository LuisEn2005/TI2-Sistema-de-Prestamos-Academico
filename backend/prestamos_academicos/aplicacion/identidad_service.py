"""Casos de uso del contexto Identidad (RF01, RF02, RF03)."""

from datetime import date

from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from ..dominio.identidad import (
    PerfilAdministrativo, PerfilDocente, PerfilEstudiante, PerfilGestorInventario,
    Permiso, ServicioAutorizacionRol, Usuario,
)
from ..dominio.shared_kernel import PoliticaServicioId, RolUsuario
from . import validacion as v
from .errores import Conflicto, ErrorAplicacion, NoAutenticado, NoEncontrado, SinPermiso

MIN_PASSWORD = 8
_HASH_FICTICIO = generate_password_hash("sin-usuario")


def validar_password(password):
    if not isinstance(password, str) or len(password) < MIN_PASSWORD:
        raise ErrorAplicacion(
            f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres.", 400)
    if len(password) > 200:
        raise ErrorAplicacion("La contraseña es demasiado larga.", 400)
    return password


def validar_correo(correo):
    correo = v.texto({"correo": correo}, "correo", maximo=160, etiqueta="correo").lower()
    local, _, dominio = correo.partition("@")
    if not local or "." not in dominio or " " in correo:
        raise ErrorAplicacion("El correo electrónico no es válido.", 400)
    return correo


class IdentidadApplicationService:
    def __init__(self, fabrica_uow):
        self._uow = fabrica_uow
        self.autorizacion = ServicioAutorizacionRol()

    # -- autenticación ---------------------------------------------------
    def autenticar(self, correo, password):
        if not isinstance(correo, str) or not isinstance(password, str):
            raise NoAutenticado()
        with self._uow() as uow:
            usuario = uow.usuarios.find_by_email(correo)
            hash_guardado = uow.usuarios.password_hash_de(usuario.id.valor) if usuario else None
        # Se verifica siempre un hash para no revelar si el correo existe.
        ok = check_password_hash(hash_guardado or _HASH_FICTICIO, password)
        if not (usuario and hash_guardado and ok):
            raise NoAutenticado()
        if not usuario.activo:
            raise NoAutenticado("La cuenta está desactivada. Consulte con un gestor.")
        return usuario

    def usuario_de_sesion(self, usuario_id, version_sesion=None):
        """Carga el usuario con sus roles vigentes; None si ya no puede acceder."""
        with self._uow() as uow:
            usuario = uow.usuarios.find_by_id(usuario_id)
        return usuario if (
            usuario and usuario.activo
            and (version_sesion is None or usuario.versionSesion == version_sesion)
        ) else None

    def permisos_de(self, usuario):
        return self.autorizacion.permisosDeRoles(usuario.roles or [])

    def cambiar_password(self, usuario_id, actual, nueva):
        validar_password(nueva)
        with self._uow() as uow:
            hash_guardado = uow.usuarios.password_hash_de(usuario_id)
            if not hash_guardado or not check_password_hash(hash_guardado, actual or ""):
                raise NoAutenticado("La contraseña actual no es correcta.")
            usuario = uow.usuarios.find_by_id(usuario_id)
            usuario.invalidarSesiones()
            uow.usuarios.save(usuario, generate_password_hash(nueva))
            uow.commit()

    # -- gestión de usuarios (RF01) ---------------------------------------
    def _politica_id(self, uow, rol):
        politica = uow.politicas.find_by_rol(rol)
        return politica.id if politica else None

    def _aplicar_perfil(self, uow, usuario, rol, datos, existente_politica=None):
        datos = v.objeto(datos, f"el perfil {rol.value}")
        campos_perfil = {
            RolUsuario.ESTUDIANTE: {"codigo_estudiante", "matricula_vigente",
                                    "politica_servicio_id"},
            RolUsuario.DOCENTE: {"codigo_empleado", "tipo_contrato",
                                 "vinculacion_vigente", "politica_servicio_id"},
            RolUsuario.ADMINISTRATIVO: {"codigo_empleado", "cargo_administrativo",
                                        "vinculacion_vigente", "politica_servicio_id"},
            RolUsuario.GESTOR_INVENTARIO: {"codigo_empleado", "area_responsable",
                                           "fecha_asignacion"},
        }
        v.campos(datos, campos_perfil[rol], f"el perfil {rol.value}")
        politica = existente_politica or self._politica_id(uow, rol)
        if "politica_servicio_id" in datos:
            solicitada = datos["politica_servicio_id"]
            if type(solicitada) is not int or uow.politicas.find_by_id(solicitada) is None:
                raise ErrorAplicacion("La política de servicio indicada no existe.", 400)
            if uow.politicas.find_by_id(solicitada).rolAplicable != rol:
                raise ErrorAplicacion("La política indicada no corresponde a este perfil.", 400)
            politica = PoliticaServicioId(solicitada)

        if rol == RolUsuario.ESTUDIANTE:
            previo = usuario.perfilEstudiante
            usuario.perfilEstudiante = PerfilEstudiante(
                codigoEstudiante=v.texto(datos, "codigo_estudiante", maximo=30,
                                         etiqueta="código de estudiante"),
                matriculaVigente=v.booleano(
                    datos, "matricula_vigente",
                    defecto=previo.matriculaVigente if previo else True),
                politicaServicioId=politica)
        elif rol == RolUsuario.DOCENTE:
            previo = usuario.perfilDocente
            usuario.perfilDocente = PerfilDocente(
                codigoEmpleado=v.texto(datos, "codigo_empleado", maximo=30,
                                       etiqueta="código de empleado"),
                tipoContrato=v.texto(datos, "tipo_contrato", maximo=60,
                                     etiqueta="tipo de contrato"),
                vinculacionVigente=v.booleano(
                    datos, "vinculacion_vigente",
                    defecto=previo.vinculacionVigente if previo else True),
                politicaServicioId=politica)
        elif rol == RolUsuario.ADMINISTRATIVO:
            previo = usuario.perfilAdministrativo
            usuario.perfilAdministrativo = PerfilAdministrativo(
                codigoEmpleado=v.texto(datos, "codigo_empleado", maximo=30,
                                       etiqueta="código de empleado"),
                cargoAdministrativo=v.texto(datos, "cargo_administrativo", maximo=80,
                                            etiqueta="cargo"),
                vinculacionVigente=v.booleano(
                    datos, "vinculacion_vigente",
                    defecto=previo.vinculacionVigente if previo else True),
                politicaServicioId=politica)
        else:
            previo = usuario.perfilGestorInventario
            usuario.perfilGestorInventario = PerfilGestorInventario(
                codigoEmpleado=v.texto(datos, "codigo_empleado", maximo=30,
                                       etiqueta="código de empleado"),
                areaResponsable=v.texto(datos, "area_responsable", maximo=80,
                                        etiqueta="área responsable"),
                fechaAsignacion=v.fecha(
                    datos, "fecha_asignacion",
                    defecto=previo.fechaAsignacion if previo else date.today()))

    def _leer_rol(self, nombre):
        try:
            return RolUsuario(str(nombre).upper())
        except ValueError:
            validos = ", ".join(r.value for r in RolUsuario)
            raise ErrorAplicacion(f"Rol desconocido: {nombre!r}. Roles válidos: {validos}.", 400)

    @staticmethod
    def _perfil_de(usuario, rol):
        return {
            RolUsuario.ESTUDIANTE: usuario.perfilEstudiante,
            RolUsuario.DOCENTE: usuario.perfilDocente,
            RolUsuario.ADMINISTRATIVO: usuario.perfilAdministrativo,
            RolUsuario.GESTOR_INVENTARIO: usuario.perfilGestorInventario,
        }[rol]

    @staticmethod
    def _quitar_perfil(usuario, rol):
        campo = {
            RolUsuario.ESTUDIANTE: "perfilEstudiante",
            RolUsuario.DOCENTE: "perfilDocente",
            RolUsuario.ADMINISTRATIVO: "perfilAdministrativo",
            RolUsuario.GESTOR_INVENTARIO: "perfilGestorInventario",
        }[rol]
        setattr(usuario, campo, None)

    def _confirmar(self, uow, usuario, password_hash=None):
        try:
            guardado = uow.usuarios.save(usuario, password_hash)
            uow.commit()
            return guardado
        except IntegrityError:
            raise Conflicto("Ya existe un usuario con el mismo correo o código.")

    def registrar_usuario(self, datos):
        datos = v.objeto(datos)
        v.campos(datos, {"nombre", "correo", "password", "activo", "perfiles"})
        perfiles = v.objeto(datos.get("perfiles") or {}, "«perfiles»")
        if not perfiles:
            raise ErrorAplicacion("Indique al menos un perfil (rol) para el usuario.", 400)
        password = datos.get("password")
        if password not in (None, ""):
            validar_password(password)
        usuario = Usuario(
            nombre=v.texto(datos, "nombre", maximo=120),
            correoElectronico=validar_correo(datos.get("correo")),
            activo=v.booleano(datos, "activo", defecto=True),
            tieneSancionActivaCache=False,
        )
        with self._uow() as uow:
            if uow.usuarios.find_by_email(usuario.correoElectronico):
                raise Conflicto("Ya existe un usuario con ese correo.")
            for nombre_rol, datos_perfil in perfiles.items():
                self._aplicar_perfil(uow, usuario, self._leer_rol(nombre_rol), datos_perfil)
            usuario.sincronizarRoles()
            return self._confirmar(
                uow, usuario, generate_password_hash(password) if password else None)

    def actualizar_usuario(self, usuario_id, datos, actor):
        datos = v.objeto(datos)
        v.campos(datos, {"nombre", "correo", "password", "activo", "perfiles"})
        with self._uow() as uow:
            usuario = uow.usuarios.find_by_id(usuario_id)
            if usuario is None:
                raise NoEncontrado("El usuario no existe.")
            era_gestor_activo = usuario.activo and usuario.tieneRol(RolUsuario.GESTOR_INVENTARIO)

            if "nombre" in datos:
                usuario.nombre = v.texto(datos, "nombre", maximo=120)
            if "correo" in datos:
                nuevo = validar_correo(datos["correo"])
                otro = uow.usuarios.find_by_email(nuevo)
                if otro and otro.id.valor != usuario_id:
                    raise Conflicto("Ya existe un usuario con ese correo.")
                usuario.correoElectronico = nuevo
            if "activo" in datos:
                nuevo_activo = v.booleano(datos, "activo")
                if nuevo_activo != usuario.activo:
                    usuario.invalidarSesiones()
                usuario.activo = nuevo_activo
                if not usuario.activo and actor.id.valor == usuario_id:
                    raise ErrorAplicacion("No puede desactivar su propia cuenta.", 409)

            for nombre_rol, datos_perfil in v.objeto(
                    datos.get("perfiles") or {}, "«perfiles»").items():
                rol = self._leer_rol(nombre_rol)
                if datos_perfil is None:
                    if rol == RolUsuario.GESTOR_INVENTARIO and actor.id.valor == usuario_id:
                        raise ErrorAplicacion("No puede quitarse su propio rol de gestor.", 409)
                    self._quitar_perfil(usuario, rol)
                else:
                    previo = self._perfil_de(usuario, rol)
                    # Combina con los datos actuales para permitir ediciones parciales.
                    combinado = self._perfil_a_dict(previo) | v.objeto(datos_perfil)
                    self._aplicar_perfil(
                        uow, usuario, rol, combinado,
                        existente_politica=getattr(previo, "politicaServicioId", None))
            usuario.sincronizarRoles()
            if not usuario.roles:
                raise ErrorAplicacion("El usuario debe conservar al menos un perfil.", 400)

            sigue_gestor_activo = usuario.activo and usuario.tieneRol(RolUsuario.GESTOR_INVENTARIO)
            if era_gestor_activo and not sigue_gestor_activo \
                    and uow.usuarios.contar_gestores_activos() <= 1:
                raise Conflicto("Debe existir al menos un gestor activo en el sistema.")

            nuevo_hash = None
            if datos.get("password") not in (None, ""):
                nuevo_hash = generate_password_hash(validar_password(datos["password"]))
                usuario.invalidarSesiones()
            return self._confirmar(uow, usuario, nuevo_hash)

    @staticmethod
    def _perfil_a_dict(perfil):
        if perfil is None:
            return {}
        mapa = {
            "codigoEstudiante": "codigo_estudiante", "matriculaVigente": "matricula_vigente",
            "codigoEmpleado": "codigo_empleado", "tipoContrato": "tipo_contrato",
            "vinculacionVigente": "vinculacion_vigente",
            "cargoAdministrativo": "cargo_administrativo", "areaResponsable": "area_responsable",
        }
        return {mapa[k]: val for k, val in vars(perfil).items()
                if k in mapa and val is not None} | (
            {"fecha_asignacion": perfil.fechaAsignacion.isoformat()}
            if getattr(perfil, "fechaAsignacion", None) else {})

    def listar_usuarios(self, *, texto=None, rol=None, activo=None, habilitado=None):
        rol_enum = self._leer_rol(rol) if rol else None
        with self._uow() as uow:
            usuarios = uow.usuarios.listar(texto=texto, rol=rol_enum, activo=activo)
        if habilitado is not None:
            usuarios = [u for u in usuarios if u.estaHabilitado() == habilitado]
        return usuarios

    def obtener_usuario(self, usuario_id):
        with self._uow() as uow:
            usuario = uow.usuarios.find_by_id(usuario_id)
        if usuario is None:
            raise NoEncontrado("El usuario no existe.")
        return usuario

    def exigir_permiso(self, usuario, permiso: Permiso):
        if permiso not in self.permisos_de(usuario):
            raise SinPermiso()

    # -- arranque ---------------------------------------------------------
    def asegurar_gestor_inicial(self, correo, password, nombre="Administrador"):
        """Crea el primer gestor si el sistema aún no tiene ninguno."""
        with self._uow() as uow:
            if uow.usuarios.listar(rol=RolUsuario.GESTOR_INVENTARIO):
                return None
        return self.registrar_usuario({
            "nombre": nombre, "correo": correo, "password": password,
            "perfiles": {"GESTOR_INVENTARIO": {
                "codigo_empleado": "ADMIN-001", "area_responsable": "Administración"}},
        })
