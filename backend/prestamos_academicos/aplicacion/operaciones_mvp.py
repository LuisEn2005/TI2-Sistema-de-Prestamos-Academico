"""Casos de uso mínimos: consultar, prestar y devolver un recurso."""

from datetime import datetime, timezone

from sqlalchemy import select, update

from ..infraestructura.persistencia.modelos import PrestamoDB, RecursoDB, UsuarioDB


class ErrorOperacion(Exception):
    def __init__(self, mensaje, estado_http):
        super().__init__(mensaje)
        self.estado_http = estado_http


def listar_recursos(fabrica_sesiones):
    with fabrica_sesiones() as sesion:
        recursos = sesion.scalars(select(RecursoDB).order_by(RecursoDB.id)).all()
        return [
            {"id": r.id, "codigo": r.codigo, "nombre": r.nombre,
             "tipo": r.tipo, "disponible": r.disponible}
            for r in recursos
        ]


def listar_usuarios(fabrica_sesiones):
    with fabrica_sesiones() as sesion:
        usuarios = sesion.scalars(select(UsuarioDB).order_by(UsuarioDB.id)).all()
        return [{"id": u.id, "nombre": u.nombre} for u in usuarios]


def _fecha_iso(fecha):
    if fecha is None:
        return None
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return fecha.isoformat()


def _detalle_prestamo(sesion, prestamo):
    usuario = sesion.get(UsuarioDB, prestamo.usuario_id)
    recurso = sesion.get(RecursoDB, prestamo.recurso_id)
    return {
        "id": prestamo.id,
        "usuario_id": prestamo.usuario_id,
        "usuario": usuario.nombre,
        "recurso_id": prestamo.recurso_id,
        "recurso": recurso.nombre,
        "fecha_prestamo": _fecha_iso(prestamo.fecha_prestamo),
        "fecha_devolucion": _fecha_iso(prestamo.fecha_devolucion),
        "estado": "devuelto" if prestamo.fecha_devolucion else "activo",
    }


def listar_prestamos(fabrica_sesiones):
    with fabrica_sesiones() as sesion:
        prestamos = sesion.scalars(select(PrestamoDB).order_by(PrestamoDB.id.desc())).all()
        return [_detalle_prestamo(sesion, p) for p in prestamos]


def registrar_prestamo(fabrica_sesiones, usuario_id, recurso_id):
    with fabrica_sesiones.begin() as sesion:
        if sesion.get(UsuarioDB, usuario_id) is None:
            raise ErrorOperacion("El usuario no existe.", 404)

        resultado = sesion.execute(
            update(RecursoDB)
            .where(RecursoDB.id == recurso_id, RecursoDB.disponible.is_(True))
            .values(disponible=False)
        )
        if resultado.rowcount == 0:
            if sesion.get(RecursoDB, recurso_id) is None:
                raise ErrorOperacion("El recurso no existe.", 404)
            raise ErrorOperacion("El recurso ya está prestado.", 409)

        prestamo = PrestamoDB(usuario_id=usuario_id, recurso_id=recurso_id)
        sesion.add(prestamo)
        sesion.flush()
        return _detalle_prestamo(sesion, prestamo)


def devolver_prestamo(fabrica_sesiones, prestamo_id):
    with fabrica_sesiones.begin() as sesion:
        prestamo = sesion.get(PrestamoDB, prestamo_id)
        if prestamo is None:
            raise ErrorOperacion("El préstamo no existe.", 404)
        if prestamo.fecha_devolucion is not None:
            raise ErrorOperacion("El préstamo ya fue devuelto.", 409)

        prestamo.fecha_devolucion = datetime.now(timezone.utc)
        recurso = sesion.get(RecursoDB, prestamo.recurso_id)
        recurso.disponible = True
        sesion.flush()
        return _detalle_prestamo(sesion, prestamo)
