from sqlalchemy import func, select

from .dominio import IPrestamoRepository
from ..base_datos import mapeadores
from ..base_datos.modelos import (
    AplazamientoPrestamoDB, DetallePrestamoDB, DiaNoLaborableDB,
    ModalidadDB, PoliticaServicioDB, PrestamoDB,
)


class SqlAlchemyPrestamoRepository(IPrestamoRepository):
    def __init__(self, sesion):
        self.sesion = sesion

    # -- lectura ----------------------------------------------------------
    def _a_dominio(self, filas):
        if not filas:
            return []
        detalles = {}
        for d in self.sesion.scalars(
                select(DetallePrestamoDB).where(DetallePrestamoDB.prestamo_id.in_([f.id for f in filas]))):
            detalles.setdefault(d.prestamo_id, []).append(d)
        contexto_filas = self.sesion.execute(
            select(
                PrestamoDB.id,
                PoliticaServicioDB.rol_aplicable,
                ModalidadDB.nombre,
            )
            .outerjoin(PoliticaServicioDB,
                       PoliticaServicioDB.id == PrestamoDB.politica_servicio_id)
            .outerjoin(ModalidadDB, ModalidadDB.id == PrestamoDB.modalidad_id)
            .where(PrestamoDB.id.in_([f.id for f in filas]))
        ).all()
        contextos = {prestamo_id: (rol, modalidad) for prestamo_id, rol, modalidad
                     in contexto_filas}
        return [mapeadores.prestamo_a_dominio(
            f, detalles.get(f.id, []),
            rol=contextos.get(f.id, (None, None))[0],
            modalidad_nombre=contextos.get(f.id, (None, None))[1],
        ) for f in filas]

    def find_by_id(self, prestamo_id):
        fila = self.sesion.get(PrestamoDB, prestamo_id)
        return self._a_dominio([fila])[0] if fila else None

    def find_by_reserva_id(self, reserva_id):
        fila = self.sesion.scalar(
            select(PrestamoDB).where(PrestamoDB.reserva_id == reserva_id))
        return self._a_dominio([fila])[0] if fila else None

    def find_activos(self):
        filas = self.sesion.scalars(
            select(PrestamoDB).where(PrestamoDB.fecha_devolucion.is_(None))
            .order_by(PrestamoDB.id.desc()))
        return self._a_dominio(list(filas))

    def buscar(self, *, usuario_id=None, estado=None, hoy=None, pagina=1, limite=20):
        condiciones = []
        if usuario_id is not None:
            condiciones.append(PrestamoDB.usuario_id == usuario_id)
        if estado == "devuelto":
            condiciones.append(PrestamoDB.fecha_devolucion.is_not(None))
        elif estado in ("activo", "vencido"):
            condiciones.append(PrestamoDB.fecha_devolucion.is_(None))
            if estado == "vencido":
                condiciones.append(PrestamoDB.fecha_devolucion_esperada < hoy)
        total = self.sesion.scalar(select(func.count()).select_from(PrestamoDB).where(*condiciones))
        filas = self.sesion.scalars(
            select(PrestamoDB).where(*condiciones).order_by(PrestamoDB.id.desc())
            .limit(limite).offset((pagina - 1) * limite))
        return self._a_dominio(list(filas)), total

    def contar_items_activos(self, usuario_id):
        return self.sesion.scalar(
            select(func.count()).select_from(DetallePrestamoDB)
            .join(PrestamoDB, PrestamoDB.id == DetallePrestamoDB.prestamo_id)
            .where(PrestamoDB.usuario_id == usuario_id, DetallePrestamoDB.activo.is_(True)))

    def ultima_devolucion_item(self, item_id):
        return self.sesion.scalar(
            select(func.max(PrestamoDB.fecha_devolucion))
            .join(DetallePrestamoDB, DetallePrestamoDB.prestamo_id == PrestamoDB.id)
            .where(DetallePrestamoDB.item_id == item_id,
                   PrestamoDB.fecha_devolucion.is_not(None)))

    def registrar_aplazamiento(self, prestamo_id, cierre_id, fecha_anterior,
                               fecha_nueva, aplicado_en):
        existente = self.sesion.scalar(select(AplazamientoPrestamoDB).where(
            AplazamientoPrestamoDB.prestamo_id == prestamo_id,
            AplazamientoPrestamoDB.fecha_anterior == fecha_anterior,
            AplazamientoPrestamoDB.fecha_nueva == fecha_nueva,
        ))
        if existente:
            return existente
        fila = AplazamientoPrestamoDB(
            prestamo_id=prestamo_id, cierre_id=cierre_id,
            fecha_anterior=fecha_anterior, fecha_nueva=fecha_nueva,
            aplicado_en=aplicado_en)
        self.sesion.add(fila)
        self.sesion.flush()
        return fila

    def listar_aplazamientos(self, prestamo_id):
        filas = self.sesion.execute(
            select(AplazamientoPrestamoDB, DiaNoLaborableDB.motivo)
            .outerjoin(DiaNoLaborableDB,
                       DiaNoLaborableDB.id == AplazamientoPrestamoDB.cierre_id)
            .where(AplazamientoPrestamoDB.prestamo_id == prestamo_id)
            .order_by(AplazamientoPrestamoDB.aplicado_en,
                      AplazamientoPrestamoDB.id)
        ).all()
        return [{
            "fecha_anterior": fila.fecha_anterior.isoformat(),
            "fecha_nueva": fila.fecha_nueva.isoformat(),
            "motivo": motivo or "Ajuste del calendario laboral",
            "aplicado_en": fila.aplicado_en.isoformat(),
        } for fila, motivo in filas]

    # -- escritura --------------------------------------------------------
    def save(self, prestamo):
        fila = self.sesion.get(PrestamoDB, prestamo.id.valor) if prestamo.id else None
        if fila is None:
            fila = PrestamoDB(
                usuario_id=prestamo.usuarioId.valor,
                reserva_id=prestamo.reservaId.valor if prestamo.reservaId else None,
                politica_servicio_id=(prestamo.politicaServicioId.valor
                                      if prestamo.politicaServicioId else None),
                modalidad_id=prestamo.modalidadId.valor if prestamo.modalidadId else None,
                dias_plazo=prestamo.diasPlazo,
                fecha_devolucion_esperada=prestamo.fechaDevolucionEsperada)
            if prestamo.fechaEntrega is not None:
                fila.fecha_prestamo = prestamo.fechaEntrega
            self.sesion.add(fila)
            self.sesion.flush()
            for d in prestamo.detalles:
                self.sesion.add(DetallePrestamoDB(
                    prestamo_id=fila.id, item_id=d.itemId.valor, activo=True))
        else:
            existentes = {d.item_id: d for d in self.sesion.scalars(
                select(DetallePrestamoDB).where(DetallePrestamoDB.prestamo_id == fila.id))}
            for d in prestamo.detalles:
                fila_detalle = existentes[d.itemId.valor]
                fila_detalle.condicion = d.condicion.value if d.condicion else None
                fila_detalle.observacion = d.observacion
                fila_detalle.activo = d.condicion is None
        fila.fecha_devolucion = prestamo.fechaDevolucionReal
        fila.fecha_devolucion_esperada = prestamo.fechaDevolucionEsperada
        self.sesion.flush()
        return self.find_by_id(fila.id)
