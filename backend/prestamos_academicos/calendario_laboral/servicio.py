"""Disponibilidad, días laborables y reprogramación institucional."""

from datetime import date, timedelta

from .dominio import DiaNoLaborable, TipoCierre
from ..compartido import Conflicto, ErrorAplicacion, NoEncontrado
from ..inventario import EstadoItem
from ..reservas import EstadoReserva


MAX_RANGO_CALENDARIO = 366
NO_PRESTABLES = {
    EstadoItem.EN_MANTENIMIENTO, EstadoItem.DADO_DE_BAJA, EstadoItem.EXTRAVIADO,
}


class CalendarioLaboralApplicationService:
    def __init__(self, fabrica_uow, reloj):
        self._uow = fabrica_uow
        self.reloj = reloj

    @staticmethod
    def _vista(cierre):
        return {
            "id": cierre.id, "fecha_inicio": cierre.fechaInicio.isoformat(),
            "fecha_fin": cierre.fechaFin.isoformat(), "tipo": cierre.tipo.value,
            "motivo": cierre.motivo, "activo": cierre.activo,
        }

    @staticmethod
    def _validar_rango(inicio, fin):
        if fin < inicio:
            raise ErrorAplicacion("La fecha final no puede ser anterior a la inicial.", 400)
        if (fin - inicio).days > MAX_RANGO_CALENDARIO:
            raise ErrorAplicacion(
                f"El calendario admite hasta {MAX_RANGO_CALENDARIO} días por consulta.", 400)

    def es_laborable(self, uow, fecha):
        if fecha.weekday() >= 5:
            return False
        return not uow.calendario.listar(fecha, fecha, solo_activos=True)

    def siguiente_laborable(self, uow, fecha):
        candidato = fecha
        while not self.es_laborable(uow, candidato):
            candidato += timedelta(days=1)
        return candidato

    def fechas_institucionales(self):
        hoy = self.reloj.hoy()
        with self._uow() as uow:
            siguiente = self.siguiente_laborable(uow, hoy + timedelta(days=1))
        return {"fecha": hoy.isoformat(), "siguiente_laborable": siguiente.isoformat()}

    def validar_laborable(self, uow, fecha, etiqueta):
        if self.es_laborable(uow, fecha):
            return
        sugerida = self.siguiente_laborable(uow, fecha + timedelta(days=1))
        raise ErrorAplicacion(
            f"La {etiqueta} no es laborable. Siguiente fecha permitida: "
            f"{sugerida.isoformat()}.", 422)

    def listar_cierres(self, desde=None, hasta=None):
        with self._uow() as uow:
            return [self._vista(c) for c in uow.calendario.listar(desde, hasta)]

    def registrar_cierre(self, actor, inicio, fin, tipo, motivo):
        self._validar_rango(inicio, fin)
        try:
            tipo = TipoCierre(tipo)
        except ValueError:
            raise ErrorAplicacion("El tipo debe ser FERIADO, HUELGA u OTRO.", 400)
        if inicio < self.reloj.hoy():
            raise ErrorAplicacion("Un cierre nuevo no puede comenzar en el pasado.", 422)
        with self._uow() as uow:
            if uow.calendario.existe_solapado(inicio, fin):
                raise Conflicto("Ya existe un periodo no laborable que se superpone.")
            cierre = uow.calendario.save(DiaNoLaborable(
                fechaInicio=inicio, fechaFin=fin, tipo=tipo, motivo=motivo.strip(),
                activo=True, creadoPorUsuarioId=actor.id.valor,
                creadoEn=self.reloj.ahora()))
            self._reprogramar(uow)
            vista = self._vista(cierre)
            uow.commit()
        return vista

    def actualizar_cierre(self, cierre_id, *, activo=None, inicio=None, fin=None,
                          tipo=None, motivo=None):
        with self._uow() as uow:
            cierre = uow.calendario.find_by_id(cierre_id)
            if cierre is None:
                raise NoEncontrado("El periodo no laborable no existe.")
            nuevo_inicio = inicio or cierre.fechaInicio
            nuevo_fin = fin or cierre.fechaFin
            self._validar_rango(nuevo_inicio, nuevo_fin)
            if inicio is not None and inicio != cierre.fechaInicio and inicio < self.reloj.hoy():
                raise ErrorAplicacion(
                    "La nueva fecha inicial no puede estar en el pasado.", 422)
            if tipo is not None:
                try:
                    cierre.tipo = TipoCierre(tipo)
                except ValueError:
                    raise ErrorAplicacion("El tipo debe ser FERIADO, HUELGA u OTRO.", 400)
            if motivo is not None:
                cierre.motivo = motivo.strip()
            cierre.fechaInicio, cierre.fechaFin = nuevo_inicio, nuevo_fin
            if activo is not None:
                cierre.activo = activo
            if cierre.activo:
                if uow.calendario.existe_solapado(
                        cierre.fechaInicio, cierre.fechaFin, excluir_id=cierre.id):
                    raise Conflicto("El periodo se superpone con otro cierre activo.")
            guardado = uow.calendario.save(cierre)
            if cierre.activo:
                self._reprogramar(uow)
            vista = self._vista(guardado)
            uow.commit()
        return vista

    def rango_ocupado(self, uow, item_id, inicio, fin, excluir_reserva=None):
        reservas = uow.reservas.find_confirmadas_solapadas(
            item_id, inicio, fin, excluir_reserva)
        if reservas:
            return max(r.fechaFin for r in reservas)
        for prestamo in uow.prestamos.find_activos():
            if any(d.itemId.valor == item_id for d in prestamo.detalles):
                entrega = self.reloj.fecha_local(prestamo.fechaEntrega)
                limite = prestamo.fechaDevolucionEsperada
                if limite is not None and entrega <= fin and inicio <= limite:
                    return limite
        return None

    def siguiente_rango_libre(self, uow, item_id, inicio, fin, excluir_reserva=None):
        duracion = (fin - inicio).days
        inicio = self.siguiente_laborable(uow, inicio)
        fin = inicio + timedelta(days=duracion)
        fin = self.siguiente_laborable(uow, fin)
        while True:
            ocupado_hasta = self.rango_ocupado(
                uow, item_id, inicio, fin, excluir_reserva)
            if ocupado_hasta is None:
                return inicio, fin
            inicio = self.siguiente_laborable(uow, ocupado_hasta + timedelta(days=1))
            fin = self.siguiente_laborable(uow, inicio + timedelta(days=duracion))

    def _reprogramar(self, uow):
        ahora = self.reloj.ahora()
        ocupados_hasta = {}
        for prestamo in uow.prestamos.find_activos():
            limite = prestamo.fechaDevolucionEsperada
            if limite and not self.es_laborable(uow, limite):
                anterior = limite
                nueva = self.siguiente_laborable(uow, limite)
                cierres = uow.calendario.listar(anterior, anterior, solo_activos=True)
                prestamo.aplazarHasta(nueva)
                uow.prestamos.save(prestamo)
                uow.prestamos.registrar_aplazamiento(
                    prestamo.id.valor, cierres[0].id if cierres else None,
                    anterior, nueva, ahora)
            for detalle in prestamo.detalles:
                if prestamo.fechaDevolucionEsperada:
                    actual = ocupados_hasta.get(detalle.itemId.valor)
                    if actual is None or prestamo.fechaDevolucionEsperada > actual:
                        ocupados_hasta[detalle.itemId.valor] = prestamo.fechaDevolucionEsperada

        for reserva in (r for r in uow.reservas.listar_activas()
                        if not r.estaVencida(self.reloj.hoy())):
            anterior_inicio, anterior_fin = reserva.fechaInicio, reserva.fechaFin
            inicio, fin = anterior_inicio, anterior_fin
            if not self.es_laborable(uow, inicio):
                inicio = self.siguiente_laborable(uow, inicio)
            if not self.es_laborable(uow, fin):
                fin = self.siguiente_laborable(uow, fin)
            if reserva.estado == EstadoReserva.CONFIRMADA:
                ocupado = ocupados_hasta.get(reserva.itemId.valor)
                if ocupado is not None and inicio <= ocupado:
                    inicio = self.siguiente_laborable(uow, ocupado + timedelta(days=1))
                if fin < inicio:
                    fin = inicio
                ocupados_hasta[reserva.itemId.valor] = fin
            reserva.fechaInicio, reserva.fechaFin = inicio, fin
            uow.reservas.save(reserva)
            if (inicio, fin) != (anterior_inicio, anterior_fin):
                uow.reservas.registrar_evento(
                    reserva.id.valor, "REPROGRAMADA", ahora,
                    motivo="Reprogramación por calendario institucional.",
                    inicio_anterior=anterior_inicio, fin_anterior=anterior_fin,
                    inicio_nuevo=inicio, fin_nuevo=fin)

    def procesar_devolucion(self, uow, item_id, *, disponible):
        """Protege compromisos futuros después de una devolución real."""
        activas = [r for r in uow.reservas.find_activas_por_item(item_id)
                   if not r.estaVencida(self.reloj.hoy())]
        ahora = self.reloj.ahora()
        if not disponible:
            for reserva in activas:
                if reserva.estado == EstadoReserva.CONFIRMADA:
                    reserva.cancelar(
                        "El recurso fue devuelto dañado o reportado como perdido.")
                    tipo = "CANCELADA"
                else:
                    reserva.rechazar(
                        "El recurso fue devuelto dañado o reportado como perdido.")
                    tipo = "RECHAZADA"
                uow.reservas.save(reserva)
                uow.reservas.registrar_evento(
                    reserva.id.valor, tipo, ahora, motivo=reserva.motivoResolucion)
            return

        ocupado_hasta = self.reloj.hoy()
        for reserva in (r for r in activas if r.estado == EstadoReserva.CONFIRMADA):
            anterior_inicio, anterior_fin = reserva.fechaInicio, reserva.fechaFin
            inicio, fin = anterior_inicio, anterior_fin
            if inicio <= ocupado_hasta:
                inicio = self.siguiente_laborable(
                    uow, ocupado_hasta + timedelta(days=1))
                if fin < inicio:
                    fin = inicio
            ocupado_hasta = fin
            if (inicio, fin) != (anterior_inicio, anterior_fin):
                reserva.fechaInicio, reserva.fechaFin = inicio, fin
                uow.reservas.save(reserva)
                uow.reservas.registrar_evento(
                    reserva.id.valor, "REPROGRAMADA", ahora,
                    motivo="Reprogramación por devolución posterior a la prevista.",
                    inicio_anterior=anterior_inicio, fin_anterior=anterior_fin,
                    inicio_nuevo=inicio, fin_nuevo=fin)

    def calendario_item(self, item_id, desde, hasta):
        self._validar_rango(desde, hasta)
        with self._uow() as uow:
            item = uow.items.find_by_id(item_id)
            if item is None:
                raise NoEncontrado("El recurso no existe.")
            confirmadas = [r for r in uow.reservas.find_activas_por_item(item_id)
                           if r.estado == EstadoReserva.CONFIRMADA
                           and not r.estaVencida(self.reloj.hoy())]
            prestamos = [p for p in uow.prestamos.find_activos()
                         if any(d.itemId.valor == item_id for d in p.detalles)]
            prestado_sin_plazo = item.estado == EstadoItem.PRESTADO and not any(
                p.fechaDevolucionEsperada is not None for p in prestamos)
            dias = []
            fecha = desde
            while fecha <= hasta:
                estado = "DISPONIBLE"
                if (item.estado in NO_PRESTABLES or prestado_sin_plazo
                        or not self.es_laborable(uow, fecha)):
                    estado = "NO_DISPONIBLE"
                elif any(p.fechaDevolucionEsperada is not None
                         and self.reloj.fecha_local(p.fechaEntrega) <= fecha
                         <= p.fechaDevolucionEsperada for p in prestamos):
                    estado = "NO_DISPONIBLE"
                elif any(r.fechaInicio <= fecha <= r.fechaFin for r in confirmadas):
                    estado = "RESERVADO"
                dias.append({"fecha": fecha.isoformat(), "estado": estado})
                fecha += timedelta(days=1)
            return {"item_id": item_id, "codigo": item.codigo,
                    "item": item.nombre, "dias": dias}

    def solicitudes_item(self, item_id, desde, hasta):
        self._validar_rango(desde, hasta)
        with self._uow() as uow:
            reservas = [r for r in uow.reservas.find_activas_por_item(item_id)
                        if r.estado == EstadoReserva.PENDIENTE
                        and not r.estaVencida(self.reloj.hoy())
                        and r.fechaInicio <= hasta and r.fechaFin >= desde]
            nombres = uow.usuarios.nombres_de([r.usuarioId.valor for r in reservas])
            return [{
                "id": r.id.valor, "usuario_id": r.usuarioId.valor,
                "usuario": nombres.get(r.usuarioId.valor),
                "rol_solicitante": r.rolSolicitante.value,
                "fecha_inicio": r.fechaInicio.isoformat(),
                "fecha_fin": r.fechaFin.isoformat(),
                "fecha_solicitud": r.fechaSolicitud.isoformat(),
            } for r in reservas]

    def inventario_fecha(self, fecha, *, texto=None, tipo=None, estado=None,
                         pagina=1, limite=15):
        """Vista protegida: disponibilidad derivada e identidad del responsable."""
        with self._uow() as uow:
            items, _ = uow.items.buscar(
                texto=texto, tipo=tipo, categoria=None, estado=None,
                pagina=1, limite=100_000)
            prestamos = uow.prestamos.find_activos()
            nombres = uow.usuarios.nombres_de(
                [p.usuarioId.valor for p in prestamos]
                + [r.usuarioId.valor for item in items
                   for r in uow.reservas.find_activas_por_item(item.id.valor)])
            filas = []
            for item in items:
                asignacion = None
                estado_fecha = "DISPONIBLE"
                if item.estado in NO_PRESTABLES or not self.es_laborable(uow, fecha):
                    estado_fecha = "NO_DISPONIBLE"
                else:
                    prestamo = next((p for p in prestamos if any(
                        d.itemId.valor == item.id.valor for d in p.detalles)
                        and p.fechaDevolucionEsperada is not None
                        and self.reloj.fecha_local(p.fechaEntrega) <= fecha
                        <= max(p.fechaDevolucionEsperada, self.reloj.hoy())), None)
                    confirmadas = uow.reservas.find_confirmadas_solapadas(
                        item.id.valor, fecha, fecha)
                    if prestamo:
                        estado_fecha = "PRESTADO"
                        asignacion = {
                            "tipo": "PRESTAMO",
                            "usuario": nombres.get(prestamo.usuarioId.valor),
                            "fecha_inicio": self.reloj.fecha_local(
                                prestamo.fechaEntrega).isoformat(),
                            "fecha_fin": prestamo.fechaDevolucionEsperada.isoformat(),
                            "prestamo_id": prestamo.id.valor,
                        }
                    elif confirmadas:
                        reserva = confirmadas[0]
                        estado_fecha = "RESERVADO"
                        asignacion = {
                            "tipo": "RESERVA",
                            "usuario": nombres.get(reserva.usuarioId.valor),
                            "fecha_inicio": reserva.fechaInicio.isoformat(),
                            "fecha_fin": reserva.fechaFin.isoformat(),
                            "reserva_id": reserva.id.valor,
                        }
                    elif item.estado == EstadoItem.PRESTADO:
                        estado_fecha = "PRESTADO"
                pendientes = uow.reservas.find_pendientes_solapadas(
                    item.id.valor, fecha, fecha)
                if estado and estado_fecha != estado:
                    continue
                filas.append({
                    "id": item.id.valor,
                    "codigo": item.codigo,
                    "nombre": item.nombre,
                    "categoria": item.categoria,
                    "tipo": item.TIPO,
                    "estado_fisico": item.estado.value,
                    "estado_fecha": estado_fecha,
                    "asignacion": asignacion,
                    "solicitudes_pendientes": len(pendientes),
                    "atributos": {k: valor for k, valor in
                                  item.atributosEspecificos().items()
                                  if valor is not None},
                })
            total = len(filas)
            inicio = (pagina - 1) * limite
            return {"items": filas[inicio:inicio + limite], "total": total,
                    "pagina": pagina, "limite": limite,
                    "fecha": fecha.isoformat()}
