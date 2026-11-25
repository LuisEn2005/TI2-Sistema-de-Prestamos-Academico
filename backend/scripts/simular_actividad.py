"""Simula actividad realista del 1-oct al 24-nov-2026 sobre la base de demostración.

Préstamos, devoluciones, sanciones y solicitudes ocurren hasta el 24-nov. Al cierre quedan
reservas ya confirmadas o pendientes que empiezan del 25 al 30-nov y algunas en diciembre,
préstamos activos y vencidos, y sanciones vigentes (por atraso, daño y pérdida).

Borra solo las acciones (reservas, préstamos, sanciones, cierres), conserva ítems y
usuarios (el padrón de `datos_demo`), y genera la historia a través de la API real con
un reloj simulado: cada paso pasa por las mismas validaciones que en producción.
La semilla es fija, así que cada ejecución produce exactamente la misma historia.

Uso (con el servidor detenido):  cd backend && .venv/bin/python scripts/simular_actividad.py
"""

import heapq
import itertools
import os
import random
import shutil
import sqlite3
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prestamos_academicos.compartido.reloj import Reloj  # noqa: E402
from prestamos_academicos.configuracion import cargar_configuracion  # noqa: E402
from prestamos_academicos.web import create_app  # noqa: E402

LIMA = ZoneInfo("America/Lima")
CLAVE = "demo1234"
ADMIN = "admin@escuela.edu"
LUIS, LORENZO = "luis.ramos@escuela.edu", "lorenzo.quispe@escuela.edu"
DOCENTE = "yessenia.yari@escuela.edu"
DIEGO, RODRIGO = "diego.canqui@escuela.edu", "rodrigo.ramos@escuela.edu"
IN_SITU, EXTERNA = "In situ (en sala)", "Externa (a domicilio)"
INICIO, HOY = date(2026, 10, 1), date(2026, 11, 24)
FERIADO = date(2026, 10, 8)
CUPO = {"ESTUDIANTE": 3, "DOCENTE": 5}

ACCIONES = ["aplazamientos_prestamo", "detalles_prestamo", "sanciones", "prestamos",
            "eventos_reserva", "reservas", "dias_no_laborables"]

# Qué pide cada quién (con pesos: los recursos populares salen más).
LIBROS = {"LIB-CLRS": 5, "LIB-CLEAN": 4, "LIB-DDIA": 3, "LIB-OS": 4, "LIB-NET": 3,
          "LIB-DB": 4, "LIB-AIMA": 3, "LIB-GOF": 3}
EXTERNO_EQUIPO = {"EQ-RPI-001": 3, "EQ-ARD-001": 3, "EQ-ESP-001": 2}
EN_SALA = {"EQ-LAP-002": 6, "EQ-META": 3, "EQ-RPI-001": 2, "EQ-ARD-001": 2,
           "EQ-ESP-001": 2, "EQ-SW-001": 2, "EQ-RTR-001": 2, "EQ-CAM-001": 1,
           "MAT-USBC-001": 2, "MAT-HDMI-001": 1}
KITS_EN_SALA = [["EQ-ARD-001", "MAT-JMP-001", "MAT-BRD-001"], ["EQ-SW-001", "MAT-ETH-001"],
                ["EQ-RTR-001", "MAT-ETH-001"], ["EQ-LAP-002", "MAT-USBC-001"]]
CLASE_DOCENTE = [["EQ-PRO-001", "MAT-HDMI-001"], ["EQ-PRO-001", "MAT-HDMI-001", "MAT-PWR-001"],
                 ["MOB-PIZ-001"], ["EQ-CAM-001"]]
RECHAZOS = {
    "LIB": ["El ejemplar queda para consulta en sala durante la semana de exámenes.",
            "El ejemplar está separado para el curso de la docente esa semana.",
            "Hay otra solicitud previa para el mismo ejemplar en esas fechas."],
    "OTRO": ["El equipo está asignado a una práctica de laboratorio ese día.",
             "Mantenimiento preventivo programado para esa fecha.",
             "El recurso quedó comprometido para una sustentación de tesis.",
             "La solicitud excede el uso permitido para el curso; coordine con el docente."],
}
RETIROS = ["Ya no lo necesito; cambié de tema.", "Conseguí un ejemplar en la biblioteca central.",
           "Me equivoqué de fechas.", "El trabajo se pospuso."]
CANCELACIONES = ["Se reprogramó la práctica del curso.", "Ya no podré recogerlo ese día.",
                 "El grupo decidió usar otro equipo."]
CIERRES = ["Presentó constancia médica que justifica el atraso.",
           "Justificó el atraso por viaje académico con constancia de la escuela.",
           "Se levanta por acuerdo de la dirección de escuela."]
DANOS = {"EQ": ["Carcasa rajada en una esquina.", "No enciende; posible daño en la fuente.",
                "Puerto USB flojo."],
         "MAT": ["Conectores rotos.", "Cable pelado en un extremo.", "Pines doblados."]}
PERDIDAS = ["Reporta que lo dejó olvidado en el transporte público.",
            "Indica que se le extravió durante una mudanza.",
            "Lo perdió en el campus; no apareció en objetos perdidos."]
REPOSICIONES = ["Repuso el ejemplar con uno nuevo de la misma edición.",
                "Pagó el costo de reposición en tesorería; se adjunta el recibo.",
                "Entregó un ejemplar equivalente aprobado por la coordinación."]


class RelojSimulado(Reloj):
    def __init__(self):
        super().__init__("America/Lima")
        self.instante = None

    def ahora(self):
        return self.instante


def laborable(dia):
    return dia.weekday() < 5 and dia != FERIADO


def siguiente_laborable(dia, saltos=1):
    while saltos:
        dia += timedelta(days=1)
        saltos -= laborable(dia)
    return dia


def a_laborable(dia):
    return dia if laborable(dia) else siguiente_laborable(dia)


class Simulacion:
    def __init__(self, app, reloj, semilla=2026):
        self.app, self.reloj = app, reloj
        self.c = app.test_client()
        self.rnd = random.Random(semilla)
        self.cola, self.seq = [], itertools.count()
        self.dia = None
        self.tokens = {}
        # Modelo propio del estado, para pedir solo operaciones válidas.
        self.ocupacion = {}      # código -> {ref: (desde, hasta)}
        self.carga = {}          # correo -> recursos prestados + reservas activas
        self.sancion_hasta = {}  # correo -> último día sancionado (conservador)
        self.activos = {}        # id préstamo -> (correo, fecha límite)
        self.en_mantenimiento = set()   # no se reserva ni presta en ninguna fecha

    # -- reloj y agenda --------------------------------------------------------------
    def agendar(self, dia, hora, fn, *args, **kwargs):
        instante = datetime.combine(dia, time.fromisoformat(hora), LIMA)
        heapq.heappush(self.cola, (instante, next(self.seq), fn, args, kwargs))

    def correr(self, fin):
        while self.cola and self.cola[0][0] <= fin:
            instante, _, fn, args, kwargs = heapq.heappop(self.cola)
            self._avanzar(instante)
            fn(*args, **kwargs)

    def _avanzar(self, instante):
        # El cron de expiración corre a las 00:01 de cada día calendario.
        while self.dia is None or instante.date() > self.dia:
            self.dia = INICIO if self.dia is None else self.dia + timedelta(days=1)
            self._fijar(datetime.combine(self.dia, time(0, 1), LIMA))
            self.app.extensions["servicios"].reservas.expirar_vencidas()
        self._fijar(instante)

    def _fijar(self, instante):
        nuevo = instante.astimezone(timezone.utc)
        assert self.reloj.instante is None or nuevo >= self.reloj.instante, nuevo
        self.reloj.instante = nuevo

    @property
    def hoy(self):
        return self.reloj.instante.astimezone(LIMA).date()

    def hora(self, desde, hasta):
        """Hora aleatoria HH:MM entre dos horas enteras."""
        minutos = self.rnd.randrange(desde * 60, hasta * 60)
        return f"{minutos // 60:02d}:{minutos % 60:02d}"

    def mas_tarde(self, minutos_min, minutos_max, tope="17:50"):
        """Hora de hoy algo después de la actual, o None si ya no alcanza el día."""
        ahora = self.reloj.instante.astimezone(LIMA)
        luego = ahora + timedelta(minutes=self.rnd.randint(minutos_min, minutos_max))
        if luego.date() != ahora.date():
            return "23:59" if tope >= "23:00" else None
        return luego.strftime("%H:%M") if luego.strftime("%H:%M") <= tope else None

    # -- API ---------------------------------------------------------------------------
    def _llamar(self, metodo, url, quien=None, cuerpo=None):
        r = getattr(self.c, metodo)(url, json=cuerpo,
                                    headers=self.sesion(quien) if quien else None)
        if r.status_code not in (200, 201):
            raise SystemExit(f"[{self.reloj.instante.astimezone(LIMA):%Y-%m-%d %H:%M}] "
                             f"{metodo.upper()} {url} {cuerpo} -> {r.status_code}: {r.get_json()}")
        return r.get_json()

    def sesion(self, correo):
        espacio = {ADMIN: "ADMINISTRACION"}.get(correo, "PERSONAL")
        if correo.startswith("@"):                       # «@luis…» = Luis en inventario
            correo, espacio = correo[1:], "INVENTARIO"
        clave = (correo, espacio)
        if clave not in self.tokens:
            r = self.c.post("/api/auth/login", json={
                "correo": correo, "password": CLAVE, "espacio": espacio})
            assert r.status_code == 200, r.get_json()
            self.tokens[clave] = {"Authorization": f"Bearer {r.get_json()['token']}"}
        return self.tokens[clave]

    def gestor(self, para=None):
        """Luis atiende por la mañana y Lorenzo por la tarde; nadie se atiende a sí mismo."""
        turno = LUIS if self.reloj.instante.astimezone(LIMA).hour < 13 else LORENZO
        if turno == para:
            turno = LORENZO if turno == LUIS else LUIS
        return "@" + turno

    def cargar_catalogos(self):
        self.items = {i["codigo"]: i["id"] for i in
                      self._llamar("get", "/api/items?limite=100")["items"]}
        self.modalidades = {m["nombre"]: m["id"] for m in
                            self._llamar("get", "/api/modalidades", ADMIN)}
        usuarios = self._llamar("get", "/api/usuarios", ADMIN)
        self.ids = {u["correo"]: u["id"] for u in usuarios}
        self.estudiantes = [u["correo"] for u in usuarios if "ESTUDIANTE" in u["roles"]
                            and u["correo"] not in (LORENZO, RODRIGO)]

    # -- modelo ------------------------------------------------------------------------
    def libre(self, codigo, desde, hasta):
        return codigo not in self.en_mantenimiento and all(hasta < a or desde > b for a, b in self.ocupacion.get(codigo, {}).values())

    def ocupar(self, codigo, ref, desde, hasta):
        self.ocupacion.setdefault(codigo, {})[ref] = (desde, hasta)

    def liberar(self, codigo, ref):
        self.ocupacion.get(codigo, {}).pop(ref, None)

    def habilitado(self, correo, cantidad=1):
        cupo = CUPO["DOCENTE" if correo == DOCENTE else "ESTUDIANTE"]
        vencido = any(c == correo and limite < self.hoy for c, limite in self.activos.values())
        return (self.carga.get(correo, 0) + cantidad <= cupo and not vencido
                and self.sancion_hasta.get(correo, date.min) < self.hoy)

    def elegir(self, pesos, desde, hasta):
        libres = {c: p for c, p in pesos.items() if self.libre(c, desde, hasta)}
        if not libres:
            return None
        return self.rnd.choices(list(libres), weights=list(libres.values()))[0]

    # -- reservas ----------------------------------------------------------------------
    def reservar(self, correo, codigo, desde, hasta, modalidad, destino="entregar", **plan):
        """`destino`: entregar | rechazar | retirar | cancelar | no_recoger."""
        r = self._llamar("post", "/api/reservas", correo, {
            "item_id": self.items[codigo], "modalidad_id": self.modalidades[modalidad],
            "fecha_inicio": desde.isoformat(), "fecha_fin": hasta.isoformat()})
        ref = f"r{r['id']}"
        self.ocupar(codigo, ref, desde, hasta)
        self.carga[correo] = self.carga.get(correo, 0) + 1
        reserva = dict(id=r["id"], ref=ref, correo=correo, codigo=codigo, desde=desde,
                       hasta=hasta, modalidad=modalidad, plan=plan)
        if destino == "retirar":
            hora = self.mas_tarde(20, 240)
            if hora:
                return self.agendar(self.hoy, hora, self._retirar, reserva)
            destino = "rechazar"
        hora = self.mas_tarde(30, 200)
        dia = self.hoy if hora else siguiente_laborable(self.hoy)
        if dia >= desde:                       # sin tiempo de atenderla antes del inicio
            dia, hora = self.hoy, self.mas_tarde(5, 15, tope="23:00")
        self.agendar(dia, hora or self.hora(8, 10), self._atender, reserva, destino)

    def _soltar(self, reserva):
        self.liberar(reserva["codigo"], reserva["ref"])
        self.carga[reserva["correo"]] -= 1

    def _retirar(self, reserva):
        self._llamar("post", f"/api/reservas/{reserva['id']}/retiro", reserva["correo"],
                     {"motivo": self.rnd.choice(RETIROS)})
        self._soltar(reserva)

    def _atender(self, reserva, destino):
        url = f"/api/reservas/{reserva['id']}"
        if destino == "rechazar":
            self._llamar("post", f"{url}/rechazo", self.gestor(reserva["correo"]),
                         {"motivo": self.rnd.choice(
                             RECHAZOS["LIB" if reserva["codigo"].startswith("LIB") else "OTRO"])})
            return self._soltar(reserva)
        self._llamar("post", f"{url}/confirmacion", self.gestor(reserva["correo"]), {})
        if destino == "cancelar":
            hora = self.mas_tarde(30, 300, tope="21:00")
            if hora:
                return self.agendar(self.hoy, hora, self._cancelar, reserva)
            dia = siguiente_laborable(self.hoy)
            if dia < reserva["desde"]:
                return self.agendar(dia, self.hora(9, 20), self._cancelar, reserva)
            return self.agendar(self.hoy, "21:30", self._cancelar, reserva)
        if destino == "no_recoger":       # el cron la expira la madrugada siguiente
            return self.agendar(reserva["desde"] + timedelta(days=1), "00:02",
                                self._soltar, reserva)
        self.agendar(reserva["desde"], self.hora(8, 11), self._entregar_reserva, reserva)

    def _cancelar(self, reserva):
        self._llamar("post", f"/api/reservas/{reserva['id']}/cancelacion", reserva["correo"],
                     {"motivo": self.rnd.choice(CANCELACIONES)})
        self._soltar(reserva)

    def _entregar_reserva(self, reserva):
        p = self._llamar("post", f"/api/reservas/{reserva['id']}/prestamo",
                         self.gestor(reserva["correo"]), {})
        self.liberar(reserva["codigo"], reserva["ref"])
        self._prestamo_entregado(p, reserva["correo"], [reserva["codigo"]],
                                 reserva["modalidad"], ya_contado=True, **reserva["plan"])

    # -- préstamos ---------------------------------------------------------------------
    def prestar(self, correo, codigos, modalidad, **plan):
        p = self._llamar("post", "/api/prestamos", self.gestor(correo), {
            "usuario_id": self.ids[correo], "item_ids": [self.items[c] for c in codigos],
            "modalidad_id": self.modalidades[modalidad]})
        self._prestamo_entregado(p, correo, codigos, modalidad, **plan)

    def _prestamo_entregado(self, p, correo, codigos, modalidad, ya_contado=False,
                            atraso=None, danado=False, nunca=False, perdido=None):
        limite = date.fromisoformat(p["fecha_limite"])
        if not ya_contado:
            self.carga[correo] = self.carga.get(correo, 0) + len(codigos)
        self.activos[p["id"]] = (correo, limite)
        if modalidad == IN_SITU:
            dia, hora = self.hoy, self.mas_tarde(90, 240) or "17:55"
        else:
            if atraso is None:
                tirada = self.rnd.random()
                atraso = (0 if tirada < 0.78 else self.rnd.randint(1, 4) if tirada < 0.95
                          else self.rnd.randint(6, 12))
                # Algunos préstamos recientes siguen sin devolverse al cierre (vencidos).
                nunca = nunca or (date(2026, 11, 9) <= limite < HOY and self.rnd.random() < 0.25)
            a_tiempo = limite - timedelta(days=self.rnd.choice([0, 0, 0, 1, 2]))
            while not laborable(a_tiempo):
                a_tiempo -= timedelta(days=1)
            a_tiempo = max(a_tiempo, siguiente_laborable(self.hoy))
            dia = (date(2027, 1, 1) if nunca
                   else a_laborable(limite + timedelta(days=atraso)) if atraso else a_tiempo)
            # Un atraso no puede pisar la reserva ya confirmada de otra persona.
            if dia > limite and not all(self.libre(c, limite + timedelta(days=1), dia)
                                        for c in codigos):
                dia = a_tiempo
            hora = self.hora(8, 18)
        hasta = max(dia, limite)
        for codigo in codigos:
            self.ocupar(codigo, f"p{p['id']}", self.hoy, hasta)
        if dia <= HOY:
            self.agendar(dia, hora, self._devolver, p["id"], correo, codigos, danado, perdido)

    def _devolver(self, prestamo_id, correo, codigos, danado, perdido=None):
        for c in codigos:
            self.liberar(c, f"p{prestamo_id}")
        # Solo se daña lo que puede pasar unos días en mantenimiento sin afectar reservas.
        roto = None
        if danado or (correo not in (LORENZO, RODRIGO) and self.rnd.random() < 0.04):
            roto = next((c for c in codigos if c.startswith(("EQ", "MAT"))
                         and self.libre(c, self.hoy, self.hoy + timedelta(days=10))), None)
        # Un libro llevado a casa se pierde rara vez (el estudiante viene a reportarlo).
        # `perdido` es la reposición del guion: (fecha, monto) o False para no reponer.
        if perdido is None and not roto and correo not in (LORENZO, RODRIGO) \
                and self.rnd.random() < 0.02:
            libro = next((c for c in codigos if c.startswith("LIB")
                          and self.libre(c, self.hoy, self.hoy + timedelta(days=30))), None)
            if libro:
                perdido = (siguiente_laborable(self.hoy, self.rnd.randint(4, 9))
                           if self.rnd.random() < 0.5 else False, None)
        extraviado = next((c for c in codigos if c.startswith("LIB")), None) if perdido else None
        for c in codigos:   # lo devuelto recién se presta desde el siguiente día laborable
            self.ocupar(c, f"p{prestamo_id}", self.hoy, self.hoy)
        condiciones = [
            {"item_id": self.items[c], "condicion": "DANADO",
             "observacion": self.rnd.choice(DANOS[c.split("-")[0]])}
            if c == roto else
            {"item_id": self.items[c], "condicion": "PERDIDO",
             "observacion": self.rnd.choice(PERDIDAS)}
            if c == extraviado else {"item_id": self.items[c], "condicion": "BUEN_ESTADO"}
            for c in codigos]
        r = self._llamar("post", f"/api/prestamos/{prestamo_id}/devolucion",
                         self.gestor(correo), {"condiciones": condiciones})
        self.activos.pop(prestamo_id)
        self.carga[correo] -= len(codigos)
        if r.get("sancion_generada_id"):
            atraso = r.get("dias_atraso") or 1
            self.sancion_hasta[correo] = self.hoy + timedelta(days=atraso + 1)
            if correo == LORENZO or (correo != RODRIGO and self.rnd.random() < 0.35):
                dia = siguiente_laborable(self.hoy, self.rnd.randint(1, 2))
                if dia < self.hoy + timedelta(days=atraso):
                    self.agendar(dia, self.hora(9, 17), self._cerrar_sancion,
                                 r["sancion_generada_id"], correo)
        if roto:
            hora = self.mas_tarde(10, 25, tope="23:00")
            self.agendar(self.hoy, hora, self._sancion_dano, correo, prestamo_id, roto)
        if extraviado:
            self.en_mantenimiento.add(extraviado)          # extraviado: no se ofrece más
            hora = self.mas_tarde(10, 25, tope="23:00")
            self.agendar(self.hoy, hora, self._sancion_perdida, correo, prestamo_id,
                         extraviado, *perdido)

    def _sancion_perdida(self, correo, prestamo_id, codigo, repone, monto):
        """Solo monto: el usuario queda bloqueado hasta reponer el libro."""
        s = self._llamar("post", "/api/sanciones", self.gestor(correo), {
            "usuario_id": self.ids[correo], "prestamo_id": prestamo_id,
            "item_id": self.items[codigo],
            "motivo": f"Pérdida del ejemplar {codigo}; debe reponerlo o pagar su costo.",
            "monto": str(monto or self.rnd.choice([145, 180, 210, 260, 320]))})
        self.sancion_hasta[correo] = date.max
        if repone and repone <= HOY:
            self.agendar(repone, self.hora(9, 16), self._repuesto, s["id"], correo, codigo)

    def _repuesto(self, sancion_id, correo, codigo):
        self._llamar("post", f"/api/sanciones/{sancion_id}/cierre", ADMIN,
                     {"resolucion": self.rnd.choice(REPOSICIONES)})
        self.sancion_hasta[correo] = self.hoy
        self._llamar("post", f"/api/items/{self.items[codigo]}/estado", self.gestor(),
                     {"estado": "DISPONIBLE"})
        self.en_mantenimiento.discard(codigo)

    def _sancion_dano(self, correo, prestamo_id, codigo):
        dias = self.rnd.randint(3, 7)
        nombre = {"EQ": "el equipo", "MAT": "el material"}[codigo.split("-")[0]]
        self._llamar("post", "/api/sanciones", self.gestor(correo), {
            "usuario_id": self.ids[correo], "prestamo_id": prestamo_id,
            "item_id": self.items[codigo],
            "motivo": f"Devolvió {nombre} {codigo} dañado.", "dias": dias})
        self.sancion_hasta[correo] = max(self.sancion_hasta.get(correo, date.min),
                                         self.hoy + timedelta(days=dias + 1))
        arreglo = siguiente_laborable(self.hoy, self.rnd.randint(3, 6))
        self.en_mantenimiento.add(codigo)
        self.agendar(arreglo, self.hora(9, 12), self._reparado, codigo)

    def _reparado(self, codigo):
        self._llamar("post", f"/api/items/{self.items[codigo]}/estado", self.gestor(),
                     {"estado": "DISPONIBLE"})
        self.en_mantenimiento.discard(codigo)

    def _cerrar_sancion(self, sancion_id, correo):
        self._llamar("post", f"/api/sanciones/{sancion_id}/cierre", ADMIN,
                     {"resolucion": self.rnd.choice(CIERRES)})
        self.sancion_hasta[correo] = self.hoy

    def _feriado(self):
        self._llamar("post", "/api/dias-no-laborables", ADMIN, {
            "fecha_inicio": FERIADO.isoformat(), "fecha_fin": FERIADO.isoformat(),
            "tipo": "FERIADO", "motivo": "Combate de Angamos"})
        # La API reprograma lo que vencía ese día; el modelo hace lo mismo.
        nuevo = siguiente_laborable(FERIADO)
        for pid, (correo, limite) in list(self.activos.items()):
            if limite == FERIADO:
                self.activos[pid] = (correo, nuevo)
                for claims in self.ocupacion.values():
                    if f"p{pid}" in claims:
                        desde, hasta = claims[f"p{pid}"]
                        claims[f"p{pid}"] = (desde, max(hasta, nuevo))

    # -- llegadas aleatorias -----------------------------------------------------------
    def llega_estudiante(self):
        """Un estudiante se acerca (en persona o desde la web) a pedir algo."""
        correo = self.rnd.choice(self.estudiantes)
        if not self.habilitado(correo):
            return
        tirada = self.rnd.random()
        if tirada < 0.45:                                   # reserva de libro externa
            desde = siguiente_laborable(self.hoy, self.rnd.randint(1, 3))
            hasta = a_laborable(desde + timedelta(days=self.rnd.randint(3, 7)))
            if (hasta - desde).days > 7:
                hasta = desde + timedelta(days=7)
                if not laborable(hasta):
                    return
            pesos = {**LIBROS, **EXTERNO_EQUIPO} if self.rnd.random() < 0.3 else LIBROS
            codigo = self.elegir(pesos, desde, hasta)
            if codigo:
                self.reservar(correo, codigo, desde, hasta, EXTERNA, self._destino())
        elif tirada < 0.70:                                 # reserva en sala
            desde = siguiente_laborable(self.hoy, self.rnd.randint(1, 2))
            codigo = self.elegir(EN_SALA, desde, desde)
            if codigo:
                self.reservar(correo, codigo, desde, desde, IN_SITU, self._destino())
        elif tirada < 0.88:                                 # en ventanilla, para usar en sala
            kit = (self.rnd.choice(KITS_EN_SALA) if self.rnd.random() < 0.3
                   else [self.elegir(EN_SALA, self.hoy, self.hoy)])
            if None not in kit and self.habilitado(correo, len(kit)) and all(
                    self.libre(c, self.hoy, self.hoy) for c in kit):
                self.prestar(correo, kit, IN_SITU)
        else:                                               # en ventanilla, a domicilio
            codigo = self.elegir({**LIBROS, **EXTERNO_EQUIPO}, self.hoy,
                                 self.hoy + timedelta(days=20))
            if codigo:
                self.prestar(correo, [codigo], EXTERNA)

    def _destino(self):
        return self.rnd.choices(["entregar", "rechazar", "retirar", "cancelar", "no_recoger"],
                                weights=[78, 8, 5, 4, 5])[0]

    def llega_docente(self):
        if not self.habilitado(DOCENTE, 3):
            return
        if self.rnd.random() < 0.75:                        # material para su clase de hoy
            kit = self.rnd.choice(CLASE_DOCENTE)
            if all(self.libre(c, self.hoy, self.hoy) for c in kit):
                self.prestar(DOCENTE, kit, IN_SITU)
        else:
            codigo = self.elegir({**LIBROS, "EQ-CAM-001": 2}, self.hoy,
                                 self.hoy + timedelta(days=16))
            if codigo:
                self.prestar(DOCENTE, [codigo], EXTERNA, atraso=0)

    def programar_dias(self):
        dia = INICIO
        while dia <= HOY:
            if laborable(dia):
                for _ in range(self.rnd.randint(4, 8)):
                    self.agendar(dia, self.hora(8, 18), self.llega_estudiante)
                if dia.weekday() in (0, 2, 4) and self.rnd.random() < 0.7:
                    self.agendar(dia, self.hora(8, 10), self.llega_docente)
            dia += timedelta(days=1)

    # -- Lorenzo como estudiante: un historial completo y fijo --------------------------
    # -- escenas fijas: historial de Lorenzo y el estado con que cierra el periodo -------
    def programar_guion(self):
        d = lambda mes, dia: date(2026, mes, dia)  # noqa: E731
        apartados = [("LIB-CLRS", d(10, 5), d(10, 9)), ("EQ-LAP-002", d(10, 15), d(10, 15)),
                     ("EQ-RPI-001", d(10, 19), d(10, 30)), ("LIB-GOF", d(11, 4), d(11, 10)),
                     ("LIB-OS", d(11, 12), d(11, 19)), ("EQ-META", d(11, 20), d(11, 20)),
                     ("LIB-CLEAN", d(10, 1), d(10, 9)), ("EQ-ESP-001", d(11, 9), d(11, 24)),
                     ("LIB-NET", d(10, 26), d(11, 6)), ("LIB-AIMA", d(11, 12), d(12, 31))]
        for codigo, desde, hasta in apartados:    # que el azar no se los lleve
            self.ocupar(codigo, f"guion-{codigo}", desde, hasta)

        def reservar(correo, codigo, *args, **kw):
            self.liberar(codigo, f"guion-{codigo}")
            self.reservar(correo, codigo, *args, **kw)

        def prestar(correo, codigo, *args, **kw):
            self.liberar(codigo, f"guion-{codigo}")
            self.prestar(correo, [codigo], *args, **kw)

        LQ = LORENZO
        self.agendar(d(10, 1), "19:40", reservar, LQ, "LIB-CLRS", d(10, 5), d(10, 9), EXTERNA,
                     "entregar", atraso=0)
        self.agendar(d(10, 14), "12:15", reservar, LQ, "EQ-LAP-002", d(10, 15), d(10, 15),
                     IN_SITU)
        self.agendar(d(10, 19), "10:20", prestar, LQ, "EQ-RPI-001", EXTERNA, atraso=3)
        self.agendar(d(11, 3), "10:30", reservar, LQ, "LIB-GOF", d(11, 4), d(11, 10), EXTERNA,
                     "retirar")
        self.agendar(d(11, 11), "18:30", reservar, LQ, "LIB-OS", d(11, 12), d(11, 19), EXTERNA,
                     "entregar", nunca=True)
        self.agendar(d(11, 17), "08:05", reservar, LQ, "EQ-META", d(11, 20), d(11, 20), IN_SITU)

        # Vence el 8-10: el feriado que se registra el 5-10 lo reprograma.
        self.agendar(d(10, 1), "08:15", prestar, DIEGO, "LIB-CLEAN", EXTERNA, atraso=0)
        # Devuelve con atraso pocos días antes del cierre: sanción vigente al 24-11.
        self.agendar(d(11, 9), "10:05", prestar, RODRIGO, "EQ-ESP-001", EXTERNA, atraso=5)

        # Pérdidas: una repuesta a los pocos días y otra que sigue pendiente al cierre.
        def prestar_a_quien_pueda(codigo, **plan):
            correo = next(c for c in self.estudiantes if self.habilitado(c))
            # Sin liberar lo apartado: nadie más debe reservar un libro que se perderá.
            self.prestar(correo, [codigo], EXTERNA, atraso=0, **plan)
        self.agendar(d(10, 26), "11:20", prestar_a_quien_pueda, "LIB-NET",
                     perdido=(d(11, 5), 185))
        self.agendar(d(11, 12), "15:40", prestar_a_quien_pueda, "LIB-AIMA",
                     perdido=(False, 240))
        # Solicitudes de fin de jornada que quedan pendientes para el día siguiente.
        self.agendar(HOY, "17:35", self.solicitud_pendiente)
        self.agendar(HOY, "17:48", self.solicitud_pendiente)
        # Reservas que empiezan del 25 al 30-11 y algunas en diciembre: las de la mañana se
        # confirman en el día; las de la tarde de hoy quedan pendientes al cierre.
        for dia in (d(11, 18), d(11, 19), d(11, 20), d(11, 23), HOY):
            for _ in range(self.rnd.randint(3, 4)):
                self.agendar(dia, self.hora(9, 14), self.reserva_futura)
        self.agendar(HOY, "10:30", self.reserva_futura, docente=True)
        self.agendar(HOY, "17:10", self.reserva_futura)
        self.agendar(HOY, "17:25", self.reserva_futura)

    def reserva_futura(self, docente=False):
        correo = DOCENTE if docente else self.rnd.choice(self.estudiantes)
        if not self.habilitado(correo):
            return
        # Casi todas empiezan dentro de la semana siguiente al cierre; pocas, en diciembre.
        desde = siguiente_laborable(self.hoy, self.rnd.choice([1, 2, 3, 4, 5, 5, 6, 8, 11]))
        if desde <= HOY:
            return
        if docente and self.rnd.random() < 0.6:            # equipo para una clase futura
            codigo = self.elegir({"EQ-PRO-001": 3, "EQ-CAM-001": 1}, desde, desde)
            return codigo and self.reservar(correo, codigo, desde, desde, IN_SITU)
        if docente or self.rnd.random() < 0.6:             # libro a domicilio
            maximo = 14 if docente else 7
            hasta = a_laborable(desde + timedelta(days=self.rnd.randint(3, maximo)))
            if (hasta - desde).days > maximo:
                return
            codigo = self.elegir(LIBROS, desde, hasta)
            return codigo and self.reservar(correo, codigo, desde, hasta, EXTERNA)
        codigo = self.elegir(EN_SALA, desde, desde)        # equipo en sala, un día
        return codigo and self.reservar(correo, codigo, desde, desde, IN_SITU)

    def solicitud_pendiente(self):
        desde = siguiente_laborable(self.hoy, 2)
        for correo in self.rnd.sample(self.estudiantes, len(self.estudiantes)):
            codigo = self.elegir(EN_SALA, desde, desde) if self.habilitado(correo) else None
            if codigo:
                return self.reservar(correo, codigo, desde, desde, IN_SITU)


def ruta_sqlite(url):
    if not url or not url.startswith("sqlite:///"):
        raise SystemExit(f"Este script solo trabaja con SQLite (DATABASE_URL={url!r}).")
    return Path(url.removeprefix("sqlite:///"))


def limpiar(ruta):
    if not ruta.exists():
        return              # base nueva: create_app la crea con migraciones y padrón
    respaldo = ruta.with_name(f"{ruta.name}.bak-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(ruta, respaldo)
    print(f"Respaldo: {respaldo}")
    with sqlite3.connect(ruta) as con:   # una transacción: todo o nada
        for tabla in ACCIONES:
            con.execute(f"DELETE FROM {tabla}")
        con.execute("UPDATE items SET estado='DISPONIBLE' "
                    "WHERE estado IN ('PRESTADO','EN_MANTENIMIENTO','EXTRAVIADO')")
        con.execute("UPDATE usuarios SET tiene_sancion_activa_cache=0")


def main():
    config = cargar_configuracion()
    ruta = ruta_sqlite(config.database_url)
    limpiar(ruta)

    reloj = RelojSimulado()
    reloj.instante = datetime(2026, 9, 30, 13, 0, tzinfo=timezone.utc)
    app = create_app(config.database_url, datos_demo=True,
                     secret_key=os.environ.get("SECRET_KEY") or "simulacion", reloj=reloj)
    with sqlite3.connect(ruta) as con:   # cuentas dadas de alta antes del ciclo
        con.execute("UPDATE usuarios SET creado_en='2026-09-21 14:00:00'")

    s = Simulacion(app, reloj)
    s.cargar_catalogos()
    s.agendar(date(2026, 10, 5), "11:00", s._feriado)
    s.programar_guion()
    s.programar_dias()
    s.correr(datetime.combine(HOY, time(18, 30), LIMA))

    with sqlite3.connect(ruta) as con:
        for tabla in ACCIONES:
            print(f"{tabla:24} {con.execute(f'SELECT count(*) FROM {tabla}').fetchone()[0]}")
        print("préstamos por estado:", dict(con.execute(
            "SELECT CASE WHEN fecha_devolucion IS NOT NULL THEN 'DEVUELTO' "
            "WHEN fecha_devolucion_esperada < ? THEN 'VENCIDO' ELSE 'ACTIVO' END e, count(*) "
            "FROM prestamos GROUP BY e", (HOY.isoformat(),)).fetchall()))
        print("reservas por estado: ", dict(con.execute(
            "SELECT estado, count(*) FROM reservas GROUP BY estado").fetchall()))
        print("sanciones por estado:", dict(con.execute(
            "SELECT estado, count(*) FROM sanciones GROUP BY estado").fetchall()))


if __name__ == "__main__":
    main()
