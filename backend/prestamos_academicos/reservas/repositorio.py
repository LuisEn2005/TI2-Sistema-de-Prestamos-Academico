"""Persistencia SQLAlchemy de reservas."""

from sqlalchemy import func, select

from .dominio import ESTADOS_ACTIVOS, EstadoReserva, IReservaRepository
from ..base_datos import mapeadores
from ..base_datos.modelos import ReservaDB


class SqlAlchemyReservaRepository(IReservaRepository):
    def __init__(self, sesion):
        self.sesion = sesion

    def save(self, reserva):
        fila = self.sesion.get(ReservaDB, reserva.id.valor) if reserva.id else ReservaDB()
        fila.usuario_id = reserva.usuarioId.valor
        fila.item_id = reserva.itemId.valor
        fila.rol_solicitante = reserva.rolSolicitante.value
        fila.fecha_solicitud = reserva.fechaSolicitud
        fila.fecha_reserva = reserva.fechaReserva
        fila.estado = reserva.estado.value
        self.sesion.add(fila)
        self.sesion.flush()
        return mapeadores.reserva_a_dominio(fila)

    def find_by_id(self, reserva_id):
        fila = self.sesion.get(ReservaDB, reserva_id)
        return mapeadores.reserva_a_dominio(fila) if fila else None

    def buscar(self, *, usuario_id=None, estado=None, pagina=1, limite=20):
        condiciones = []
        if usuario_id is not None:
            condiciones.append(ReservaDB.usuario_id == usuario_id)
        if estado is not None:
            condiciones.append(ReservaDB.estado == EstadoReserva(estado).value)
        total = self.sesion.scalar(
            select(func.count()).select_from(ReservaDB).where(*condiciones))
        filas = self.sesion.scalars(
            select(ReservaDB).where(*condiciones)
            .order_by(ReservaDB.id.desc())
            .limit(limite).offset((pagina - 1) * limite))
        return [mapeadores.reserva_a_dominio(f) for f in filas], total

    def find_vencidas(self, hoy):
        filas = self.sesion.scalars(
            select(ReservaDB).where(
                ReservaDB.estado.in_([e.value for e in ESTADOS_ACTIVOS]),
                ReservaDB.fecha_reserva < hoy,
            ).order_by(ReservaDB.id))
        return [mapeadores.reserva_a_dominio(f) for f in filas]

    def find_activa_por_item(self, item_id):
        fila = self.sesion.scalar(select(ReservaDB).where(
            ReservaDB.item_id == item_id,
            ReservaDB.estado.in_([e.value for e in ESTADOS_ACTIVOS]),
        ).order_by(ReservaDB.id).limit(1))
        return mapeadores.reserva_a_dominio(fila) if fila else None

    def contar_activas_usuario(self, usuario_id):
        return self.sesion.scalar(select(func.count()).select_from(ReservaDB).where(
            ReservaDB.usuario_id == usuario_id,
            ReservaDB.estado.in_([e.value for e in ESTADOS_ACTIVOS]),
        ))
