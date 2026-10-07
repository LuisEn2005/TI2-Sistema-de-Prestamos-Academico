from sqlalchemy import func, or_, select

from ....dominio.identidad import IUsuarioRepository
from ....dominio.shared_kernel import RolUsuario
from .. import mapeador
from ..modelos import (
    PerfilAdministrativoDB, PerfilDocenteDB, PerfilEstudianteDB,
    PerfilGestorInventarioDB, UsuarioDB,
)

_TABLAS = {
    "estudiante": PerfilEstudianteDB,
    "docente": PerfilDocenteDB,
    "administrativo": PerfilAdministrativoDB,
    "gestor": PerfilGestorInventarioDB,
}
_ROL_A_TABLA = {
    RolUsuario.ESTUDIANTE: "estudiante",
    RolUsuario.DOCENTE: "docente",
    RolUsuario.ADMINISTRATIVO: "administrativo",
    RolUsuario.GESTOR_INVENTARIO: "gestor",
}


def _like(texto):
    escapado = texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escapado.lower()}%"


class SqlAlchemyUsuarioRepository(IUsuarioRepository):
    def __init__(self, sesion):
        self.sesion = sesion

    # -- lectura ----------------------------------------------------------
    def _perfiles_de(self, ids):
        perfiles = {i: {} for i in ids}
        if not ids:
            return perfiles
        for clave, tabla in _TABLAS.items():
            for fila in self.sesion.scalars(select(tabla).where(tabla.usuario_id.in_(ids))):
                perfiles[fila.usuario_id][clave] = fila
        return perfiles

    def _a_dominio(self, filas):
        perfiles = self._perfiles_de([f.id for f in filas])
        return [mapeador.usuario_a_dominio(f, perfiles[f.id]) for f in filas]

    def find_by_id(self, usuario_id):
        fila = self.sesion.get(UsuarioDB, usuario_id)
        return self._a_dominio([fila])[0] if fila else None

    def find_by_email(self, correo):
        fila = self.sesion.scalar(
            select(UsuarioDB).where(func.lower(UsuarioDB.correo) == correo.strip().lower()))
        return self._a_dominio([fila])[0] if fila else None

    def password_hash_de(self, usuario_id):
        fila = self.sesion.get(UsuarioDB, usuario_id)
        return fila.password_hash if fila else None

    def listar(self, *, texto=None, rol=None, activo=None):
        consulta = select(UsuarioDB).order_by(UsuarioDB.nombre, UsuarioDB.id)
        if texto:
            patron = _like(texto)
            consulta = consulta.where(or_(
                func.lower(UsuarioDB.nombre).like(patron, escape="\\"),
                func.lower(UsuarioDB.correo).like(patron, escape="\\"),
            ))
        if activo is not None:
            consulta = consulta.where(UsuarioDB.activo.is_(activo))
        if rol is not None:
            tabla = _TABLAS[_ROL_A_TABLA[rol]]
            consulta = consulta.where(UsuarioDB.id.in_(select(tabla.usuario_id)))
        return self._a_dominio(list(self.sesion.scalars(consulta)))

    def contar_gestores_activos(self):
        return self.sesion.scalar(
            select(func.count()).select_from(PerfilGestorInventarioDB)
            .join(UsuarioDB, UsuarioDB.id == PerfilGestorInventarioDB.usuario_id)
            .where(UsuarioDB.activo.is_(True))
        )

    # -- escritura --------------------------------------------------------
    def save(self, usuario, password_hash=None):
        fila = self.sesion.get(UsuarioDB, usuario.id.valor) if usuario.id else None
        if fila is None:
            fila = UsuarioDB()
            self.sesion.add(fila)
        fila.nombre = usuario.nombre
        fila.correo = usuario.correoElectronico
        fila.activo = usuario.activo
        fila.version_sesion = usuario.versionSesion
        fila.tiene_sancion_activa_cache = bool(usuario.tieneSancionActivaCache)
        if password_hash is not None:
            fila.password_hash = password_hash
        self.sesion.flush()

        e, d, a, g = (usuario.perfilEstudiante, usuario.perfilDocente,
                      usuario.perfilAdministrativo, usuario.perfilGestorInventario)
        pid = lambda p: p.valor if p else None  # noqa: E731
        self._sincronizar("estudiante", fila.id, e and dict(
            codigo_estudiante=e.codigoEstudiante, matricula_vigente=bool(e.matriculaVigente),
            politica_servicio_id=pid(e.politicaServicioId)))
        self._sincronizar("docente", fila.id, d and dict(
            codigo_empleado=d.codigoEmpleado, tipo_contrato=d.tipoContrato,
            vinculacion_vigente=bool(d.vinculacionVigente),
            politica_servicio_id=pid(d.politicaServicioId)))
        self._sincronizar("administrativo", fila.id, a and dict(
            codigo_empleado=a.codigoEmpleado, cargo_administrativo=a.cargoAdministrativo,
            vinculacion_vigente=bool(a.vinculacionVigente),
            politica_servicio_id=pid(a.politicaServicioId)))
        self._sincronizar("gestor", fila.id, g and dict(
            codigo_empleado=g.codigoEmpleado, area_responsable=g.areaResponsable,
            fecha_asignacion=g.fechaAsignacion))
        self.sesion.flush()
        return self.find_by_id(fila.id)

    def _sincronizar(self, clave, usuario_id, datos):
        tabla = _TABLAS[clave]
        existente = self.sesion.get(tabla, usuario_id)
        if datos is None:
            if existente is not None:
                self.sesion.delete(existente)
            return
        if existente is None:
            existente = tabla(usuario_id=usuario_id)
            self.sesion.add(existente)
        for campo, valor in datos.items():
            setattr(existente, campo, valor)
