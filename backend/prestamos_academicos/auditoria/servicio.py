"""Consulta del historial unificado (RF17).

Agrega, sin persistir nada nuevo, los movimientos que ya guardan los contextos de
préstamos, reservas y sanciones, y los deja consultables por tipo, estado, rango de
fechas, usuario e ítem. El titular ve solo lo suyo; quien tiene
CONSULTAR_HISTORIAL_GLOBAL ve el de cualquiera.
"""

from typing import Optional

from .dominio import HistorialMovimiento, TipoEvento
from ..compartido.reloj import Reloj
from ..identidad import Permiso

# shortcut: cada fuente se trae acotada por los filtros y la unión se ordena en
# memoria. Suficiente a escala de laboratorio/biblioteca (RNF05); si el historial
# creciera mucho, conviene una vista SQL UNION ALL con paginación en la base.
_MAX_FUENTE = 1000


class HistorialApplicationService:
    def __init__(self, fabrica_uow, identidad, reloj: Optional[Reloj] = None):
        self._uow = fabrica_uow
        self._identidad = identidad
        self.reloj = reloj or Reloj()

    def _ve_todo(self, actor):
        return Permiso.CONSULTAR_HISTORIAL_GLOBAL in self._identidad.permisos_de(actor)

    def consultar(self, actor, *, tipo=None, estado=None, desde=None, hasta=None,
                  usuario_id=None, item_id=None, pagina=1, limite=20):
        objetivo = usuario_id if self._ve_todo(actor) else actor.id.valor
        with self._uow() as uow:
            movimientos = []
            if tipo in (None, TipoEvento.RESERVA):
                movimientos += self._reservas(uow, objetivo, item_id)
            if tipo in (None, TipoEvento.PRESTAMO):
                movimientos += self._prestamos(uow, objetivo, item_id)
            if tipo in (None, TipoEvento.SANCION) and item_id is None:
                movimientos += self._sanciones(uow, objetivo)
            uow.commit()  # persiste el cierre automático de sanciones vencidas

        if estado:
            objetivo_estado = estado.lower()
            movimientos = [m for m in movimientos if m.estado.lower() == objetivo_estado]
        if desde:
            movimientos = [m for m in movimientos if m.fecha >= desde]
        if hasta:
            movimientos = [m for m in movimientos if m.fecha <= hasta]

        movimientos.sort(key=lambda m: (m.fecha, m.referencia_id), reverse=True)
        total = len(movimientos)
        inicio = (pagina - 1) * limite
        pagina_movimientos = movimientos[inicio:inicio + limite]
        return {
            "movimientos": [m.a_json() for m in pagina_movimientos],
            "total": total, "pagina": pagina, "limite": limite,
        }

    # -- fuentes -----------------------------------------------------------------
    def _reservas(self, uow, usuario_id, item_id):
        reservas, _ = uow.reservas.buscar(
            usuario_id=usuario_id, estado=None, solo_activas=False,
            pagina=1, limite=_MAX_FUENTE)
        if item_id is not None:
            reservas = [r for r in reservas if r.itemId.valor == item_id]
        nombres = uow.usuarios.nombres_de([r.usuarioId.valor for r in reservas])
        items = uow.items.find_by_ids([r.itemId.valor for r in reservas])
        movimientos = []
        for r in reservas:
            it = items.get(r.itemId.valor)
            detalle = f"Reserva del {r.fechaInicio.isoformat()} al {r.fechaFin.isoformat()}"
            if r.motivoResolucion:
                detalle += f" · {r.motivoResolucion}"
            movimientos.append(HistorialMovimiento(
                tipo=TipoEvento.RESERVA, referencia_id=r.id.valor,
                fecha=self.reloj.fecha_local(r.fechaSolicitud), estado=r.estado.value,
                detalle=detalle, usuario_id=r.usuarioId.valor,
                usuario=nombres.get(r.usuarioId.valor), item_id=r.itemId.valor,
                codigo=it.codigo if it else None, item=it.nombre if it else None))
        return movimientos

    def _prestamos(self, uow, usuario_id, item_id):
        prestamos, _ = uow.prestamos.buscar(
            usuario_id=usuario_id, estado=None, hoy=self.reloj.hoy(),
            pagina=1, limite=_MAX_FUENTE)
        if item_id is not None:
            prestamos = [p for p in prestamos
                         if any(d.itemId.valor == item_id for d in p.detalles)]
        nombres = uow.usuarios.nombres_de([p.usuarioId.valor for p in prestamos])
        items = uow.items.find_by_ids(
            [d.itemId.valor for p in prestamos for d in p.detalles])
        hoy = self.reloj.hoy()
        movimientos = []
        for p in prestamos:
            if p.fechaDevolucionReal is not None:
                estado = "devuelto"
            else:
                estado = "vencido" if p.estaVencido(hoy) else "activo"
            codigos = [items[d.itemId.valor].codigo for d in p.detalles
                       if d.itemId.valor in items]
            detalle = f"Entrega de {len(p.detalles)} recurso(s): {', '.join(codigos)}"
            if p.fechaDevolucionEsperada:
                detalle += f" · límite {p.fechaDevolucionEsperada.isoformat()}"
            if p.fechaDevolucionReal is not None:
                detalle += f" · devuelto {self.reloj.fecha_local(p.fechaDevolucionReal).isoformat()}"
            visible = item_id or (p.detalles[0].itemId.valor if p.detalles else None)
            it = items.get(visible)
            movimientos.append(HistorialMovimiento(
                tipo=TipoEvento.PRESTAMO, referencia_id=p.id.valor,
                fecha=self.reloj.fecha_local(p.fechaEntrega), estado=estado,
                detalle=detalle, usuario_id=p.usuarioId.valor,
                usuario=nombres.get(p.usuarioId.valor), item_id=visible,
                codigo=it.codigo if it else None, item=it.nombre if it else None))
        return movimientos

    def _sanciones(self, uow, usuario_id):
        uow.sanciones.sincronizar_vencidas(
            self.reloj.hoy(), self.reloj.ahora(), usuario_id)
        sanciones = uow.sanciones.listar(usuario_id=usuario_id, estado=None)
        nombres = uow.usuarios.nombres_de([s.usuarioId.valor for s in sanciones])
        movimientos = []
        for s in sanciones:
            detalle = f"{s.origen.value} · {s.motivo}"
            if s.fechaFin:
                detalle += f" · hasta {s.fechaFin.isoformat()}"
            if s.resolucion:
                detalle += f" · {s.resolucion}"
            movimientos.append(HistorialMovimiento(
                tipo=TipoEvento.SANCION, referencia_id=s.id.valor,
                fecha=s.fechaInicio, estado=s.estado.value, detalle=detalle,
                usuario_id=s.usuarioId.valor, usuario=nombres.get(s.usuarioId.valor)))
        return movimientos
