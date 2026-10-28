from sqlalchemy import func, select

from .dominio import IPrestamoRepository
from ..base_datos import mapeadores
from ..base_datos.modelos import DetallePrestamoDB, PrestamoDB


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
        return [mapeadores.prestamo_a_dominio(f, detalles.get(f.id, [])) for f in filas]

    def find_by_id(self, prestamo_id):
        fila = self.sesion.get(PrestamoDB, prestamo_id)
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

    # -- escritura --------------------------------------------------------
    def save(self, prestamo):
        fila = self.sesion.get(PrestamoDB, prestamo.id.valor) if prestamo.id else None
        if fila is None:
            m = prestamo.modalidad
            fila = PrestamoDB(
                usuario_id=prestamo.usuarioId.valor,
                rol_solicitante=prestamo.rolSolicitante.value if prestamo.rolSolicitante else None,
                modalidad_id=m.modalidadOrigenId.valor if m and m.modalidadOrigenId else None,
                modalidad_nombre=m.nombre if m else None,
                modalidad_dias_plazo=m.diasPlazo if m else None,
                dias_plazo_aplicado=prestamo.diasPlazoAplicado,
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
        self.sesion.flush()
        return self.find_by_id(fila.id)
