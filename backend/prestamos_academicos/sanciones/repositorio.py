"""Persistencia SQLAlchemy de sanciones."""

from sqlalchemy import func, select, update

from .dominio import EstadoSancion, ISancionRepository, Monto, OrigenSancion, Sancion
from ..base_datos.modelos import SancionDB, UsuarioDB
from ..compartido import PrestamoId, SancionId, UsuarioId


def _a_dominio(fila):
    if fila is None:
        return None
    return Sancion(
        id=SancionId(fila.id), usuarioId=UsuarioId(fila.usuario_id),
        prestamoId=PrestamoId(fila.prestamo_id) if fila.prestamo_id else None,
        creadaPorUsuarioId=(UsuarioId(fila.creada_por_usuario_id)
                            if fila.creada_por_usuario_id else None),
        origen=OrigenSancion(fila.origen), motivo=fila.motivo,
        monto=Monto(fila.monto, fila.moneda) if fila.monto is not None else None,
        fechaInicio=fila.fecha_inicio, fechaFin=fila.fecha_fin,
        estado=EstadoSancion(fila.estado), cerradaEn=fila.cerrada_en,
        resolucion=fila.resolucion,
    )


class SqlAlchemySancionRepository(ISancionRepository):
    def __init__(self, sesion):
        self.sesion = sesion

    def save(self, sancion):
        fila = self.sesion.get(SancionDB, sancion.id.valor) if sancion.id else SancionDB()
        fila.usuario_id = sancion.usuarioId.valor
        fila.prestamo_id = sancion.prestamoId.valor if sancion.prestamoId else None
        fila.creada_por_usuario_id = (
            sancion.creadaPorUsuarioId.valor if sancion.creadaPorUsuarioId else None)
        fila.origen = sancion.origen.value
        fila.motivo = sancion.motivo
        fila.monto = sancion.monto.cantidad if sancion.monto else None
        fila.moneda = sancion.monto.moneda if sancion.monto else None
        fila.fecha_inicio = sancion.fechaInicio
        fila.fecha_fin = sancion.fechaFin
        fila.estado = sancion.estado.value
        fila.cerrada_en = sancion.cerradaEn
        fila.resolucion = sancion.resolucion
        self.sesion.add(fila)
        self.sesion.flush()
        return _a_dominio(fila)

    def find_by_id(self, sancion_id):
        return _a_dominio(self.sesion.get(SancionDB, sancion_id))

    def listar(self, *, usuario_id=None, estado=None):
        condiciones = []
        if usuario_id is not None:
            condiciones.append(SancionDB.usuario_id == usuario_id)
        if estado is not None:
            condiciones.append(SancionDB.estado == EstadoSancion(estado).value)
        filas = self.sesion.scalars(
            select(SancionDB).where(*condiciones).order_by(SancionDB.id.desc()))
        return [_a_dominio(fila) for fila in filas]

    def sincronizar_vencidas(self, hoy, ahora, usuario_id=None):
        condiciones = [
            SancionDB.estado == EstadoSancion.ACTIVA.value,
            SancionDB.fecha_fin.is_not(None),
            SancionDB.fecha_fin < hoy,
        ]
        if usuario_id is not None:
            condiciones.append(SancionDB.usuario_id == usuario_id)
        usuarios = set(self.sesion.scalars(
            select(SancionDB.usuario_id).where(*condiciones)))
        if usuarios:
            self.sesion.execute(update(SancionDB).where(*condiciones).values(
                estado=EstadoSancion.CERRADA.value, cerrada_en=ahora,
                resolucion="Cierre automático por cumplimiento del plazo."))
            for uid in usuarios:
                self.actualizar_cache_usuario(uid)
        return len(usuarios)

    def actualizar_cache_usuario(self, usuario_id):
        activa = bool(self.sesion.scalar(
            select(func.count()).select_from(SancionDB).where(
                SancionDB.usuario_id == usuario_id,
                SancionDB.estado == EstadoSancion.ACTIVA.value)))
        self.sesion.execute(update(UsuarioDB).where(
            UsuarioDB.id == usuario_id).values(tiene_sancion_activa_cache=activa))
        return activa
