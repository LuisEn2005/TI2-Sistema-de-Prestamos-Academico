"""Sanciones, bloqueos y configuración del Sprint 5."""

from datetime import timedelta

from .ayudas import ADMIN, ESTUDIANTE, EXTERNA, GESTOR_DOCENTE, IN_SITU, ApiBase


class SancionesBase(ApiBase):
    def prestar(self, h, codigo="LIB-CLRS", modalidad=EXTERNA):
        return self.cliente.post("/api/prestamos", headers=h, json={
            "usuario_id": self.usuario_id(ESTUDIANTE, h),
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
        politica = next(
            p for p in self.cliente.get("/api/politicas", headers=admin).json
            if p["rol"] == "ESTUDIANTE" and p["modalidad"] == IN_SITU)
        respuesta = self.cliente.patch(
            f"/api/politicas/{politica['id']}", headers=admin,
            json={"dias_sancion_por_dia_atraso": 2})
        self.assertEqual(respuesta.status_code, 200, respuesta.json)
        renovable = self.prestar(admin, "EQ-META", EXTERNA).json
        vencera_hoy = self.prestar(admin, "LIB-CLRS", IN_SITU).json

        self.reloj.instante += timedelta(days=2)
        devolucion = self.devolver(admin, vencera_hoy)
        self.assertEqual(devolucion.status_code, 200, devolucion.json)
        self.assertIsNotNone(devolucion.json["sancion_generada_id"])

        sanciones = self.cliente.get("/api/sanciones?estado=ACTIVA", headers=admin).json
        self.assertEqual(len(sanciones), 1)
        self.assertEqual((sanciones[0]["origen"], sanciones[0]["prestamo_id"]),
                         ("RETRASO", vencera_hoy["id"]))
        self.assertEqual((sanciones[0]["fecha_inicio"], sanciones[0]["fecha_fin"]),
                         ("2026-10-21", "2026-10-24"))

        estudiante = self.ingresar(ESTUDIANTE)
        propias = self.cliente.get("/api/sanciones", headers=estudiante).json
        self.assertEqual([s["id"] for s in propias], [sanciones[0]["id"]])
        bloqueado = self.prestar(admin, "LIB-CLEAN")
        self.assertEqual(bloqueado.status_code, 422)
        self.assertIn("sanción activa", bloqueado.json["error"])
        reserva = self.cliente.post("/api/reservas", headers=estudiante, json={
            "item_id": self.item_id("LIB-CLEAN"), "fecha_reserva": "2026-10-22"})
        self.assertEqual(reserva.status_code, 422)
        renovacion = self.cliente.post(
            f"/api/prestamos/{renovable['id']}/renovacion", headers=estudiante, json={})
        self.assertEqual(renovacion.status_code, 422)

    def test_sancion_caduca_y_habilita_nuevamente(self):
        admin = self.ingresar()
        prestamo = self.prestar(admin, modalidad=IN_SITU).json
        self.reloj.instante += timedelta(days=1)
        self.devolver(admin, prestamo)
        self.reloj.instante += timedelta(days=2)

        estudiante = self.ingresar(ESTUDIANTE)
        sancion = self.cliente.get("/api/sanciones", headers=estudiante).json[0]
        self.assertEqual(sancion["estado"], "CERRADA")
        self.assertIn("cumplimiento", sancion["resolucion"])
        self.assertEqual(self.prestar(admin, "LIB-CLEAN").status_code, 201)


class SancionManualTest(SancionesBase):
    def test_gestor_registra_y_administrador_cierra_sancion(self):
        gestor = self.ingresar(GESTOR_DOCENTE)
        uid = self.usuario_id(ESTUDIANTE)
        creada = self.cliente.post("/api/sanciones", headers=gestor, json={
            "usuario_id": uid, "origen": "DANO", "motivo": "Pantalla quebrada",
            "dias": 5, "monto": "120.50",
        })
        self.assertEqual(creada.status_code, 201, creada.json)
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
        self.assertEqual(self.prestar(admin).status_code, 201)

    def test_valida_sanciones_y_visibilidad(self):
        admin = self.ingresar()
        uid = self.usuario_id(ESTUDIANTE, admin)
        base = {"usuario_id": uid, "origen": "PERDIDA", "motivo": "No devuelto"}
        for cuerpo in (
                base,
                {**base, "origen": "RETRASO", "dias": 2},
                {**base, "dias": 0},
                {**base, "monto": -1},
                {**base, "monto": "NaN"},
                {**base, "dias": 2, "otro": True}):
            with self.subTest(cuerpo=cuerpo):
                respuesta = self.cliente.post(
                    "/api/sanciones", headers=admin, json=cuerpo)
                invalido = ("otro" in cuerpo or cuerpo.get("dias") == 0
                            or cuerpo.get("monto") in (-1, "NaN"))
                self.assertEqual(respuesta.status_code, 400 if invalido else 422)
        self.assertEqual(self.cliente.get("/api/sanciones").status_code, 401)
        self.assertEqual(self.cliente.get(
            "/api/sanciones?estado=OTRA", headers=admin).status_code, 400)
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
            f"/api/politicas/{politica['id']}", headers=admin, json={
                "max_items_simultaneos": 4, "dias_prestamo": 9,
                "dias_sancion_por_dia_atraso": 2,
            })
        self.assertEqual(actualizada.status_code, 200, actualizada.json)
        self.assertEqual((actualizada.json["max_items_simultaneos"],
                          actualizada.json["dias_prestamo"],
                          actualizada.json["dias_sancion_por_dia_atraso"]), (4, 9, 2))
        condiciones = self.cliente.get("/api/prestamos/condiciones", headers=admin, query_string={
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
        self.assertEqual(self.prestar(admin).status_code, 422)

    def test_solo_administrador_y_con_limites_validos(self):
        admin = self.ingresar()
        politica_id = self.cliente.get("/api/politicas", headers=admin).json[0]["id"]
        estudiante = self.ingresar(ESTUDIANTE)
        self.assertEqual(self.cliente.patch(
            f"/api/politicas/{politica_id}", headers=estudiante,
            json={"dias_prestamo": 2}).status_code, 403)
        for cuerpo in ({}, {"dias_prestamo": 0}, {"max_items_simultaneos": 51},
                       {"dias_sancion_por_dia_atraso": 31}, {"desconocido": 1}):
            self.assertEqual(self.cliente.patch(
                f"/api/politicas/{politica_id}", headers=admin, json=cuerpo).status_code, 400)
