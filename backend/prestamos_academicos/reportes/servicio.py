"""Reportes de acciones (nivel evento) por usuario o por ítem, en un rango de fechas.

Reúne, sin persistir nada nuevo, las acciones que ya guardan los contextos de
reservas (eventos), préstamos (entrega/devolución/aplazamientos) y sanciones
(apertura/cierre). El resultado alimenta el renderizador de PDF.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..compartido import NoEncontrado, SinPermiso
from ..compartido.reloj import Reloj
from ..identidad import Permiso
from ..sanciones.repositorio import RESOLUCION_AUTOMATICA

ETIQUETA_EVENTO_RESERVA = {
    "SOLICITADA": "Reserva solicitada",
    "CONFIRMADA": "Reserva confirmada",
    "RECHAZADA": "Reserva rechazada",
    "RETIRADA": "Solicitud retirada",
    "CANCELADA": "Reserva cancelada",
    "EXPIRADA": "Reserva expirada",
    "ENTREGADA": "Reserva entregada (préstamo creado)",
}

ORIGEN_SANCION = {"RETRASO": "Por atraso", "DANO": "Por daño", "PERDIDA": "Por pérdida"}


@dataclass
class Accion:
    fecha: str            # AAAA-MM-DD (fecha local de la acción)
    hora: Optional[str]   # HH:MM en America/Lima, o None si la fuente es solo fecha
    categoria: str        # RESERVA | PRESTAMO | SANCION
    accion: str           # etiqueta legible
    responsable: Optional[str]
    item: Optional[str]   # código del recurso, cuando aplica
    detalle: str
    usuario: Optional[str] = None  # prestatario afectado por la acción

    @property
    def orden(self):
        # Sin hora (sanciones): al final del día, tras la acción que la originó.
        return (self.fecha, self.hora or "99:99")


class ReporteApplicationService:
    def __init__(self, fabrica_uow, identidad, reloj: Optional[Reloj] = None):
        self._uow = fabrica_uow
        self._identidad = identidad
        self.reloj = reloj or Reloj()

    def _ve_todo(self, actor):
        return Permiso.CONSULTAR_HISTORIAL_GLOBAL in self._identidad.permisos_de(actor)

    # -- API pública -------------------------------------------------------------
    def datos_usuario(self, actor, usuario_id, desde, hasta):
        if not self._ve_todo(actor) and usuario_id != actor.id.valor:
            raise SinPermiso("Solo puede generar el reporte de sus propias acciones.")
        with self._uow() as uow:
            usuario = uow.usuarios.find_by_id(usuario_id)
            if usuario is None:
                raise NoEncontrado("El usuario no existe.")
            acciones = (self._acciones_reserva(uow, usuario_id=usuario_id)
                        + self._acciones_prestamo(uow, usuario_id=usuario_id)
                        + self._acciones_sancion(uow, usuario_id))
            uow.commit()
        return self._armar(actor, "usuario", usuario.nombre, desde, hasta, acciones)

    def datos_item(self, actor, item_id, desde, hasta):
        with self._uow() as uow:
            item = uow.items.find_by_id(item_id)
            if item is None:
                raise NoEncontrado("El recurso no existe.")
            acciones = (self._acciones_reserva(uow, item_id=item_id)
                        + self._acciones_prestamo(uow, item_id=item_id))
            uow.commit()
        sujeto = f"{item.codigo} — {item.nombre}"
        return self._armar(actor, "item", sujeto, desde, hasta, acciones)

    # -- ensamblado --------------------------------------------------------------
    def _armar(self, actor, tipo, sujeto, desde, hasta, acciones):
        acciones = [a for a in acciones if desde.isoformat() <= a.fecha <= hasta.isoformat()]
        acciones.sort(key=lambda a: a.orden)
        return {
            "tipo": tipo, "sujeto": sujeto,
            "desde": desde, "hasta": hasta,
            "generado_por": getattr(actor, "nombre", None),
            "generado_en": self.reloj.ahora(),
            "resumen": self._resumen(acciones),
            "acciones": acciones,
        }

    @staticmethod
    def _resumen(acciones):
        contar = lambda etiqueta: sum(1 for a in acciones if a.accion == etiqueta)
        return {
            "total": len(acciones),
            "reservas_solicitadas": contar("Reserva solicitada"),
            "reservas_confirmadas": contar("Reserva confirmada"),
            "prestamos_entregados": contar("Préstamo entregado"),
            "devoluciones_a_tiempo": contar("Préstamo devuelto a tiempo"),
            "devoluciones_tarde": contar("Préstamo devuelto con atraso"),
            "sanciones_aplicadas": contar("Sanción aplicada"),
            "sanciones_cerradas": contar("Sanción cerrada"),
        }

    # -- fuentes -----------------------------------------------------------------
    def _acciones_reserva(self, uow, *, usuario_id=None, item_id=None):
        eventos = uow.reservas.eventos_para_reporte(usuario_id=usuario_id, item_id=item_id)
        items = uow.items.find_by_ids([e["item_id"] for e in eventos])
        acciones = []
        for e in eventos:
            local = self.reloj.fecha_local(e["creado_en"])
            it = items.get(e["item_id"])
            acciones.append(Accion(
                fecha=local.isoformat(), hora=self._hora(e["creado_en"]),
                categoria="RESERVA",
                accion=ETIQUETA_EVENTO_RESERVA.get(e["tipo"], e["tipo"]),
                responsable=e["actor"], item=it.codigo if it else None,
                usuario=e["usuario_nombre"],
                detalle=" · ".join(filter(None, (
                    f"Reserva #{e['reserva_id']}",
                    f"del {e['fecha_inicio'].isoformat()} al {e['fecha_fin'].isoformat()}",
                    e["motivo"])))))
        return acciones

    def _acciones_prestamo(self, uow, *, usuario_id=None, item_id=None):
        prestamos, _ = uow.prestamos.buscar(
            usuario_id=usuario_id, estado=None, hoy=self.reloj.hoy(),
            pagina=1, limite=10_000)
        if item_id is not None:
            prestamos = [p for p in prestamos
                         if any(d.itemId.valor == item_id for d in p.detalles)]
        items = uow.items.find_by_ids(
            [d.itemId.valor for p in prestamos for d in p.detalles])
        acciones = []
        nombres = {}
        for p in prestamos:
            numero = f"Préstamo #{p.id.valor}"
            prestatario = self._nombre(uow, p.usuarioId, nombres)
            codigos = [items[d.itemId.valor].codigo for d in p.detalles
                       if d.itemId.valor in items]
            if item_id is not None and item_id in items:
                visible = items[item_id].codigo
            else:
                visible = codigos[0] if codigos else None
            entrega = self.reloj.fecha_local(p.fechaEntrega)
            acciones.append(Accion(
                fecha=entrega.isoformat(), hora=self._hora(p.fechaEntrega),
                categoria="PRESTAMO", accion="Préstamo entregado",
                responsable=self._nombre(uow, p.entregadoPorUsuarioId, nombres), item=visible, usuario=prestatario,
                detalle=" · ".join(filter(None, (
                    numero,
                    f"modalidad {p.modalidadNombre}" if p.modalidadNombre else None,
                    f"plazo {p.diasPlazo} día(s)" if p.diasPlazo else None,
                    (f"límite {p.fechaDevolucionEsperada.isoformat()}"
                     if p.fechaDevolucionEsperada else None),
                    f"{len(p.detalles)} recurso(s): {', '.join(codigos)}",
                    (f"estado {p.estado.value}"
                     if p.estado and p.estado.value != "DEVUELTO" else None))))))
            if p.fechaDevolucionReal is not None:
                devuelto = self.reloj.fecha_local(p.fechaDevolucionReal)
                atraso = (max(0, (devuelto - p.fechaDevolucionEsperada).days)
                          if p.fechaDevolucionEsperada else 0)
                acciones.append(Accion(
                    fecha=devuelto.isoformat(), hora=self._hora(p.fechaDevolucionReal),
                    categoria="PRESTAMO",
                    accion="Préstamo devuelto con atraso" if atraso else "Préstamo devuelto a tiempo",
                    responsable=self._nombre(uow, p.recibidoPorUsuarioId, nombres), item=visible, usuario=prestatario,
                    detalle=f"{numero} · " + (f"devuelto con {atraso} día(s) de atraso"
                                               if atraso else "devuelto dentro del plazo")))
            for apl in uow.prestamos.listar_aplazamientos(p.id.valor):
                aplicado = self.reloj.fecha_local(datetime.fromisoformat(apl["aplicado_en"]))
                acciones.append(Accion(
                    fecha=aplicado.isoformat(),
                    hora=self._hora(datetime.fromisoformat(apl["aplicado_en"])),
                    categoria="PRESTAMO", accion="Reprogramación por cierre",
                    responsable="Sistema", item=visible, usuario=prestatario,
                    detalle=(f"{numero} · límite {apl['fecha_anterior']} → {apl['fecha_nueva']} · "
                             f"{apl['motivo']}")))
        return acciones

    def _acciones_sancion(self, uow, usuario_id):
        acciones = []
        nombres = {}
        for s in uow.sanciones.listar(usuario_id=usuario_id, estado=None):
            # Sin creador registrado = sanción automática por atraso.
            responsable = self._nombre(uow, s.creadaPorUsuarioId, nombres) or "Sistema"
            afectado = self._nombre(uow, s.usuarioId, nombres)
            vigencia = (f"vigente del {s.fechaInicio.isoformat()} al {s.fechaFin.isoformat()}"
                        if s.fechaFin else f"vigente desde {s.fechaInicio.isoformat()}")
            acciones.append(Accion(
                fecha=s.fechaInicio.isoformat(), hora=None, categoria="SANCION",
                accion="Sanción aplicada", responsable=responsable, item=None,
                usuario=afectado,
                detalle=" · ".join(filter(None, (
                    ORIGEN_SANCION.get(s.origen.value, s.origen.value), s.motivo, vigencia,
                    f"S/ {s.monto.cantidad:.2f}" if s.monto else None,
                    f"préstamo #{s.prestamoId.valor}" if s.prestamoId else None)))))
            if s.estado.value == "CERRADA":
                cierre = (self.reloj.fecha_local(s.cerradaEn) if s.cerradaEn
                          else s.fechaFin or s.fechaInicio)
                acciones.append(Accion(
                    fecha=cierre.isoformat(), hora=self._hora(s.cerradaEn),
                    categoria="SANCION", accion="Sanción cerrada",
                    responsable=(self._nombre(uow, s.cerradaPorUsuarioId, nombres)
                                 or ("Sistema" if s.resolucion == RESOLUCION_AUTOMATICA
                                     else None)),
                    item=None, usuario=afectado,
                    detalle=s.resolucion or "Sanción levantada"))
        return acciones

    @staticmethod
    def _nombre(uow, usuario_id, cache):
        if usuario_id is None:
            return None
        if usuario_id.valor not in cache:
            u = uow.usuarios.find_by_id(usuario_id.valor)
            cache[usuario_id.valor] = u.nombre if u else None
        return cache[usuario_id.valor]

    def _hora(self, instante):
        if instante is None:
            return None
        if instante.tzinfo is None:
            from datetime import timezone
            instante = instante.replace(tzinfo=timezone.utc)
        return instante.astimezone(self.reloj.zona).strftime("%H:%M")
