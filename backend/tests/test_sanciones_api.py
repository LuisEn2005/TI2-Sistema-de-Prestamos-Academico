"""Sanciones, bloqueos y configuración del Sprint 5."""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .ayudas import ADMIN, ESTUDIANTE, EXTERNA, GESTOR, IN_SITU, ApiBase


class SancionesBase(ApiBase):
    def prestar(self, h, codigo="LIB-CLRS", modalidad=EXTERNA):
        return self.cliente.post("/api/prestamos", headers=h, json={
            "usuario_id": self.usuario_id(ESTUDIANTE),
            "item_ids": [self.item_id(codigo)],
            "modalidad_id": self.modalidad_id(modalidad),
        })

    def devolver(self, h, prestamo):
        item = prestamo["items"][0]
        return self.cliente.post(
            f"/api/prestamos/{prestamo['id']}/devolucion", headers=h,
            json={"condiciones": [{"item_id": item["item_id"],
                                    "condicion": "BUEN_ESTADO"}]})


class SancionAutomaticaTest(SancionesBase):
    def test_atraso_genera_sancion_y_bloquea_operaciones(self):
        admin = self.ingresar(ADMIN)
        respuesta = self.cliente.patch(
            "/api/politicas-rol/ESTUDIANTE", headers=admin,
            json={"dias_sancion_por_dia_atraso": 2})
        self.assertEqual(respuesta.status_code, 200, respuesta.json)
        inventario = self.ingresar(ADMIN, espacio="INVENTARIO")
        self.prestar(inventario, "EQ-META", EXTERNA)
        vencera_hoy = self.prestar(inventario, "LIB-CLRS", IN_SITU).json

        self.reloj.instante += timedelta(days=2)
        devolucion = self.devolver(inventario, vencera_hoy)
        self.assertEqual(devolucion.status_code, 200, devolucion.json)
        self.assertIsNotNone(devolucion.json["sancion_generada_id"])

        sanciones = self.cliente.get(
            "/api/sanciones?estado=ACTIVA", headers=inventario).json
        self.assertEqual(len(sanciones), 1)
        self.assertEqual((sanciones[0]["origen"], sanciones[0]["prestamo_id"]),
                         ("RETRASO", vencera_hoy["id"]))
        self.assertEqual((sanciones[0]["fecha_inicio"], sanciones[0]["fecha_fin"]),
                         ("2026-10-21", "2026-10-24"))

        estudiante = self.ingresar(ESTUDIANTE)
        propias = self.cliente.get("/api/sanciones", headers=estudiante).json
        self.assertEqual([s["id"] for s in propias], [sanciones[0]["id"]])
        bloqueado = self.prestar(inventario, "LIB-CLEAN")
        self.assertEqual(bloqueado.status_code, 422)
        self.assertIn("sanción activa", bloqueado.json["error"])
        correos = lambda ruta: [u["correo"] for u in self.cliente.get(ruta, headers=inventario).json]
        self.assertNotIn(ESTUDIANTE, correos("/api/usuarios/prestatarios"))
        todos = correos("/api/usuarios/prestatarios?todos=true")   # historial
        self.assertIn(ESTUDIANTE, todos)
        self.assertNotIn(ADMIN, todos)
        reserva = self.cliente.post("/api/reservas", headers=estudiante, json={
            "item_id": self.item_id("LIB-CLEAN"), "fecha_reserva": "2026-10-22"})
        self.assertEqual(reserva.status_code, 422)

    def test_sancion_caduca_y_habilita_nuevamente(self):
        inventario = self.ingresar(ADMIN, espacio="INVENTARIO")
        prestamo = self.prestar(inventario, modalidad=IN_SITU).json
        self.reloj.instante += timedelta(days=1)
        self.devolver(inventario, prestamo)
        self.reloj.instante += timedelta(days=2)

        estudiante = self.ingresar(ESTUDIANTE)
        sancion = self.cliente.get("/api/sanciones", headers=estudiante).json[0]
        self.assertEqual(sancion["estado"], "CERRADA")
        self.assertIn("cumplimiento", sancion["resolucion"])
        self.assertEqual(self.prestar(inventario, "LIB-CLEAN").status_code, 201)

    def test_cron_diario_cierra_sancion_al_dia_siguiente_del_fin(self):
        inventario = self.ingresar(ADMIN, espacio="INVENTARIO")
        prestamo = self.prestar(inventario, modalidad=IN_SITU).json
        self.reloj.instante += timedelta(days=1)
        self.devolver(inventario, prestamo)
        sancion = self.cliente.get("/api/sanciones", headers=inventario).json[0]

        # 00:01 en Lima del día siguiente al fin, sin ninguna petición del usuario.
        fin = date.fromisoformat(sancion["fecha_fin"])
        cron = datetime.combine(fin + timedelta(days=1), time(0, 1),
                                ZoneInfo("America/Lima")).astimezone(timezone.utc)
        self.reloj.instante = cron
        servicios = self.app.extensions["servicios"]
        servicios.reservas.expirar_vencidas()

        with servicios.reservas._uow() as uow:
            cerrada = uow.sanciones.find_by_id(sancion["id"])
            usuario = uow.usuarios.find_by_id(cerrada.usuarioId.valor)
        self.assertEqual(cerrada.estado.value, "CERRADA")
        self.assertEqual(cerrada.cerradaEn.replace(tzinfo=timezone.utc), cron)
        self.assertFalse(usuario.tieneSancionActivaCache)
        self.assertIsNone(cerrada.cerradaPorUsuarioId)   # el reporte lo muestra como «Sistema»


class SancionManualTest(SancionesBase):
    def test_gestor_registra_y_administrador_cierra_sancion(self):
        gestor = self.ingresar(GESTOR)
        uid = self.usuario_id(ESTUDIANTE)
        recurso = self.incidencia(gestor, "LIB-CLRS", "DANADO")
        creada = self.cliente.post("/api/sanciones", headers=gestor, json={
            "usuario_id": uid, **recurso, "motivo": "Pantalla quebrada",
            "dias": 5, "monto": "120.50",
        })
        self.assertEqual(creada.status_code, 201, creada.json)
        self.assertEqual(creada.json["origen"], "DANO")   # sale de la devolución
        self.assertEqual((creada.json["monto"], creada.json["moneda"]), ("120.50", "PEN"))
        self.assertEqual(creada.json["fecha_fin"], "2026-10-23")
        self.assertEqual(self.cliente.post(
            f"/api/sanciones/{creada.json['id']}/cierre", headers=gestor,
            json={"resolucion": "Repuesto"}).status_code, 403)

        admin = self.ingresar(ADMIN)
        cerrada = self.cliente.post(
            f"/api/sanciones/{creada.json['id']}/cierre", headers=admin,
            json={"resolucion": "El usuario repuso el equipo."})
        self.assertEqual(cerrada.status_code, 200, cerrada.json)
        self.assertEqual(cerrada.json["estado"], "CERRADA")
        inventario = self.ingresar(ADMIN, espacio="INVENTARIO")
        self.assertEqual(self.prestar(inventario, "LIB-CLEAN").status_code, 201)

    def test_sanciones_nuevas_se_encadenan_sin_superponerse(self):
        gestor = self.ingresar(GESTOR)
        uid = self.usuario_id(ESTUDIANTE)
        # Primero las devoluciones: con una sanción activa ya no se le podría prestar.
        r1, r2, r3, r4 = (self.incidencia(gestor, c) for c in
                          ("LIB-CLRS", "LIB-CLEAN", "LIB-GOF", "EQ-META"))
        sancionar = lambda recurso, **extra: self.cliente.post(
            "/api/sanciones", headers=gestor,
            json={"usuario_id": uid, **recurso, "motivo": "Daño", **extra}).json
        primera, segunda = sancionar(r1, dias=10), sancionar(r2, dias=5)
        self.assertEqual((primera["fecha_inicio"], primera["fecha_fin"]),
                         ("2026-10-19", "2026-10-28"))
        self.assertEqual((segunda["fecha_inicio"], segunda["fecha_fin"]),
                         ("2026-10-29", "2026-11-02"))
        # Una sanción sin plazo (solo monto) no desplaza a las siguientes.
        sancionar(r3, monto="50")
        self.assertEqual(sancionar(r4, dias=1)["fecha_inicio"], "2026-11-03")

    def test_sancion_manual_se_vincula_al_recurso_devuelto_perdido(self):
        gestor = self.ingresar(GESTOR)
        uid = self.usuario_id(ESTUDIANTE)
        sano = self.incidencia(gestor, "LIB-CLEAN", "BUEN_ESTADO")
        recurso = self.incidencia(gestor, "LIB-CLRS", "PERDIDO")

        recursos = self.cliente.get(f"/api/sanciones/recursos?usuario_id={uid}", headers=gestor)
        self.assertEqual(recursos.status_code, 200, recursos.json)
        self.assertEqual([(r["prestamo_id"], r["item_id"], r["origen"]) for r in recursos.json],
                         [(recurso["prestamo_id"], recurso["item_id"], "PERDIDA")])

        base = {"usuario_id": uid, "motivo": "Lo perdió", "dias": 3}
        enviar = lambda cuerpo: self.cliente.post("/api/sanciones", headers=gestor, json=cuerpo)
        self.assertEqual(enviar({**base, **sano}).status_code, 422)       # volvió en buen estado
        self.assertEqual(enviar({**base, **recurso, "origen": "DANO"}).status_code, 400)
        creada = enviar({**base, **recurso})
        self.assertEqual(creada.status_code, 201, creada.json)
        self.assertEqual((creada.json["origen"], creada.json["item_id"]),
                         ("PERDIDA", recurso["item_id"]))
        self.assertTrue(creada.json["recurso"].startswith("LIB-CLRS"))
        # Ya sancionado: no se ofrece de nuevo ni se puede repetir.
        self.assertEqual(self.cliente.get(
            f"/api/sanciones/recursos?usuario_id={uid}", headers=gestor).json, [])
        self.assertEqual(enviar({**base, **recurso}).status_code, 409)
        self.assertEqual(self.cliente.get(
            "/api/sanciones/recursos", headers=gestor).status_code, 400)
        self.assertEqual(self.cliente.get(
            f"/api/sanciones/recursos?usuario_id={uid}",
            headers=self.ingresar(ESTUDIANTE)).status_code, 403)

    def test_valida_sanciones_y_visibilidad(self):
        administracion = self.ingresar()
        uid = self.usuario_id(ESTUDIANTE, administracion)
        inventario = self.ingresar(ADMIN, espacio="INVENTARIO")
        recurso = self.incidencia(inventario, "LIB-CLRS", "PERDIDO")
        base = {"usuario_id": uid, **recurso, "motivo": "No devuelto"}
        sin_recurso = {"usuario_id": uid, "motivo": "No devuelto", "dias": 2}
        for cuerpo, esperado in (
                (sin_recurso, 400),                      # el recurso es obligatorio
                ({**base, "dias": 0}, 400),
                ({**base, "monto": -1}, 400),
                ({**base, "monto": "NaN"}, 400),
                ({**base, "dias": 2, "otro": True}, 400),
                (base, 422)):                            # sin duración ni monto
            with self.subTest(cuerpo=cuerpo):
                respuesta = self.cliente.post(
                    "/api/sanciones", headers=inventario, json=cuerpo)
                self.assertEqual(respuesta.status_code, esperado, respuesta.json)
        self.assertEqual(self.cliente.get("/api/sanciones").status_code, 401)
        self.assertEqual(self.cliente.get(
            "/api/sanciones?estado=OTRA", headers=inventario).status_code, 400)
        self.assertEqual(self.cliente.post(
            "/api/sanciones", headers=self.ingresar(ESTUDIANTE), json={**base, "dias": 2}
        ).status_code, 403)


class PoliticasConfigurablesTest(SancionesBase):
    def test_administrador_modifica_reglas_y_modalidades(self):
        admin = self.ingresar()
        politicas = self.cliente.get("/api/politicas", headers=admin).json
        politica = next(p for p in politicas
                         if p["rol"] == "ESTUDIANTE" and p["modalidad"] == EXTERNA)
        actualizada = self.cliente.patch(
            f"/api/politicas/{politica['id']}", headers=admin,
            json={"dias_prestamo": 9})
        self.assertEqual(actualizada.status_code, 200, actualizada.json)
        regla = self.cliente.patch(
            "/api/politicas-rol/ESTUDIANTE", headers=admin, json={
                "max_items_simultaneos": 4, "dias_sancion_por_dia_atraso": 2})
        self.assertEqual(regla.status_code, 200, regla.json)
        self.assertEqual((regla.json["max_items_simultaneos"],
                          actualizada.json["dias_prestamo"],
                          regla.json["dias_sancion_por_dia_atraso"]), (4, 9, 2))
        condiciones = self.cliente.get("/api/prestamos/condiciones", headers=admin, query_string={
            "usuario_id": self.usuario_id(ESTUDIANTE, admin),
            "modalidad_id": politica["modalidad_id"],
        })
        self.assertEqual(condiciones.status_code, 403)
        inventario = self.ingresar(ADMIN, espacio="INVENTARIO")
        condiciones = self.cliente.get(
            "/api/prestamos/condiciones", headers=inventario, query_string={
                "usuario_id": self.usuario_id(ESTUDIANTE, admin),
                "modalidad_id": politica["modalidad_id"],
            }).json
        self.assertEqual((condiciones["max_items_simultaneos"], condiciones["dias_plazo"]),
                         (4, 9))

        modalidad = self.cliente.patch(
            f"/api/modalidades/{politica['modalidad_id']}", headers=admin,
            json={"activo": False})
        self.assertEqual(modalidad.status_code, 200, modalidad.json)
        self.assertFalse(modalidad.json["activo"])
        self.assertEqual(self.prestar(inventario).status_code, 422)

    def test_solo_administrador_y_con_limites_validos(self):
        admin = self.ingresar()
        politica_id = next(
            p["id"] for p in self.cliente.get("/api/politicas", headers=admin).json
            if p["modalidad"] == EXTERNA)
        estudiante = self.ingresar(ESTUDIANTE)
        self.assertEqual(self.cliente.patch(
            f"/api/politicas/{politica_id}", headers=estudiante,
            json={"dias_prestamo": 2}).status_code, 403)
        for cuerpo in ({}, {"dias_prestamo": 0}, {"max_items_simultaneos": 51},
                       {"dias_sancion_por_dia_atraso": 31}, {"desconocido": 1}):
            self.assertEqual(self.cliente.patch(
                f"/api/politicas/{politica_id}", headers=admin, json=cuerpo).status_code, 400)
        for cuerpo in ({}, {"max_items_simultaneos": 51},
                       {"dias_sancion_por_dia_atraso": 31}, {"desconocido": 1}):
            self.assertEqual(self.cliente.patch(
                "/api/politicas-rol/ESTUDIANTE", headers=admin, json=cuerpo).status_code, 400)
