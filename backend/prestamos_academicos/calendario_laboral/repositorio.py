"""Persistencia del calendario institucional."""

from sqlalchemy import select

from .dominio import DiaNoLaborable, TipoCierre
from ..base_datos.modelos import DiaNoLaborableDB


def _dominio(fila):
    if fila is None:
        return None
    return DiaNoLaborable(
        id=fila.id, fechaInicio=fila.fecha_inicio, fechaFin=fila.fecha_fin,
        tipo=TipoCierre(fila.tipo), motivo=fila.motivo, activo=fila.activo,
        creadoPorUsuarioId=fila.creado_por_usuario_id, creadoEn=fila.creado_en)


class SqlAlchemyCalendarioRepository:
    def __init__(self, sesion):
        self.sesion = sesion

    def save(self, cierre):
        fila = self.sesion.get(DiaNoLaborableDB, cierre.id) if cierre.id else DiaNoLaborableDB()
        fila.fecha_inicio = cierre.fechaInicio
        fila.fecha_fin = cierre.fechaFin
        fila.tipo = cierre.tipo.value
        fila.motivo = cierre.motivo
        fila.activo = cierre.activo
        fila.creado_por_usuario_id = cierre.creadoPorUsuarioId
        fila.creado_en = cierre.creadoEn
        self.sesion.add(fila)
        self.sesion.flush()
        return _dominio(fila)

    def find_by_id(self, cierre_id):
        return _dominio(self.sesion.get(DiaNoLaborableDB, cierre_id))

    def listar(self, desde=None, hasta=None, solo_activos=False):
        condiciones = []
        if desde is not None:
            condiciones.append(DiaNoLaborableDB.fecha_fin >= desde)
        if hasta is not None:
            condiciones.append(DiaNoLaborableDB.fecha_inicio <= hasta)
        if solo_activos:
            condiciones.append(DiaNoLaborableDB.activo.is_(True))
        filas = self.sesion.scalars(select(DiaNoLaborableDB).where(*condiciones).order_by(
            DiaNoLaborableDB.fecha_inicio, DiaNoLaborableDB.id))
        return [_dominio(f) for f in filas]

    def existe_solapado(self, inicio, fin, excluir_id=None):
        condiciones = [
            DiaNoLaborableDB.activo.is_(True),
            DiaNoLaborableDB.fecha_inicio <= fin,
            DiaNoLaborableDB.fecha_fin >= inicio,
        ]
        if excluir_id is not None:
            condiciones.append(DiaNoLaborableDB.id != excluir_id)
        return self.sesion.scalar(
            select(DiaNoLaborableDB.id).where(*condiciones).limit(1)) is not None
