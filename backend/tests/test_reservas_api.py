"""Reservas, prioridad y entrega física."""

from datetime import timedelta

from .ayudas import ADMIN, ESTUDIANTE, EXTERNA, GESTOR_DOCENTE, ApiBase


class ReservasBase(ApiBase):
    def reservar(self, h, codigo="LIB-CLRS", fecha="2026-10-20",
                 fecha_fin="2026-10-26", **extra):
        return self.cliente.post("/api/reservas", headers=h, json={
            "item_id": self.item_id(codigo),
            "modalidad_id": self.modalidad_id(EXTERNA),
            "fecha_inicio": fecha, "fecha_fin": fecha_fin, **extra})

    def entregar(self, h, correo=ESTUDIANTE, codigo="LIB-CLRS"):
        return self.cliente.post("/api/prestamos", headers=h, json={
            "usuario_id": self.usuario_id(correo),
            "item_ids": [self.item_id(codigo)],
            "modalidad_id": self.modalidad_id(EXTERNA),
        })


class FlujoReservaTest(ReservasBase):
    def test_solicitar_confirmar_y_convertir_en_prestamo(self):
        estudiante = self.ingresar(ESTUDIANTE)
        creada = self.reservar(
            estudiante, fecha="2026-10-20", fecha_fin="2026-10-27").json
        self.assertEqual((creada["estado"], creada["rol_solicitante"]),
                         ("PENDIENTE", "ESTUDIANTE"))
        self.assertEqual(creada["fecha_inicio"], "2026-10-20")
        self.assertNotIn("fecha_expiracion", creada)
        self.assertEqual(self.estado_item("LIB-CLRS"), "DISPONIBLE")

        administrador = self.ingresar(ADMIN)
        confirmada = self.cliente.post(
            f"/api/reservas/{creada['id']}/confirmacion", headers=administrador, json={})
        self.assertEqual(confirmada.status_code, 200, confirmada.json)
        self.assertEqual(confirmada.json["estado"], "CONFIRMADA")

        self.reloj.instante += timedelta(days=1)

        prestamo = self.cliente.post(
            f"/api/reservas/{creada['id']}/prestamo", headers=administrador,
            json={})
        self.assertEqual(prestamo.status_code, 201, prestamo.json)
        self.assertEqual((prestamo.json["reserva_id"], prestamo.json["dias_plazo"]),
                         (creada["id"], 7))
        self.assertEqual(prestamo.json["fecha_limite"], "2026-10-27")
        self.assertEqual(self.estado_item("LIB-CLRS"), "PRESTADO")
        reserva = self.cliente.get(
            "/api/reservas?historial=1", headers=estudiante).json["reservas"][0]
        self.assertEqual(reserva["estado"], "CONVERTIDA")

    def test_retirar_libera_el_cupo_y_no_se_repite(self):
        estudiante = self.ingresar(ESTUDIANTE)
        reserva = self.reservar(estudiante).json
        cancelada = self.cliente.post(
            f"/api/reservas/{reserva['id']}/retiro", headers=estudiante, json={})
        self.assertEqual(cancelada.status_code, 200, cancelada.json)
        self.assertEqual(cancelada.json["estado"], "RETIRADA")
        self.assertEqual(self.estado_item("LIB-CLRS"), "DISPONIBLE")
        repetida = self.cliente.post(
            f"/api/reservas/{reserva['id']}/retiro", headers=estudiante, json={})
        self.assertEqual(repetida.status_code, 409)

    def test_expiracion_automatica_libera_el_recurso(self):
        estudiante = self.ingresar(ESTUDIANTE)
        reserva = self.reservar(estudiante, fecha="2026-10-20").json
        self.assertEqual(reserva["estado"], "PENDIENTE")
        self.assertEqual(self.cliente.get(
            "/api/reservas", headers=estudiante).json["reservas"][0]["estado"], "PENDIENTE")
        self.reloj.instante += timedelta(days=2)
        listado = self.cliente.get("/api/reservas", headers=estudiante)
        self.assertEqual(listado.status_code, 200, listado.json)
        self.assertEqual(listado.json["reservas"], [])
        historial = self.cliente.get(
            "/api/reservas?historial=1", headers=estudiante).json["reservas"]
        self.assertEqual(historial[0]["estado"], "EXPIRADA")
        self.assertEqual(self.estado_item("LIB-CLRS"), "DISPONIBLE")

    def test_comando_programado_expira_y_audita_como_sistema(self):
        estudiante = self.ingresar(ESTUDIANTE)
        reserva = self.reservar(estudiante, fecha="2026-10-20").json
        self.reloj.instante += timedelta(days=2)
        resultado = self.app.test_cli_runner().invoke(args=["expirar-reservas"])
        self.assertEqual(resultado.exit_code, 0, resultado.output)
        self.assertIn("Reservas expiradas: 1", resultado.output)
        detalle = self.cliente.get(
            f"/api/reservas/{reserva['id']}", headers=estudiante).json
        self.assertEqual(detalle["estado"], "EXPIRADA")
        self.assertEqual(detalle["eventos"][-1]["actor"], "Sistema")

    def test_varias_solicitudes_compiten_y_una_confirmacion_resuelve_el_conflicto(self):
        primera = self.reservar(self.ingresar(ESTUDIANTE))
        segunda = self.reservar(self.ingresar(GESTOR_DOCENTE))
        self.assertEqual((primera.status_code, segunda.status_code), (201, 201))
        confirmada = self.cliente.post(
            f"/api/reservas/{segunda.json['id']}/confirmacion",
            headers=self.ingresar(ADMIN), json={})
        self.assertEqual(confirmada.status_code, 200, confirmada.json)
        reservas = self.cliente.get(
            "/api/reservas?historial=1", headers=self.ingresar(ADMIN)).json["reservas"]
        estados = {r["id"]: r["estado"] for r in reservas}
        self.assertEqual(estados[primera.json["id"]], "RECHAZADA")
        self.assertEqual(estados[segunda.json["id"]], "CONFIRMADA")


class RenovacionDescartadaTest(ReservasBase):
    def test_el_endpoint_de_renovacion_ya_no_existe(self):
        prestamo = self.entregar(self.ingresar(ADMIN)).json
        respuesta = self.cliente.post(
            f"/api/prestamos/{prestamo['id']}/renovacion",
            headers=self.ingresar(ESTUDIANTE), json={})
        self.assertEqual(respuesta.status_code, 404)


class SeguridadYValidacionReservasTest(ReservasBase):
    def test_permisos_y_visibilidad(self):
        self.assertEqual(self.cliente.get("/api/reservas").status_code, 401)
        self.assertEqual(self.cliente.post("/api/reservas", json={}).status_code, 401)
        self.assertEqual(self.reservar(self.ingresar(ADMIN)).status_code, 422)

        estudiante = self.ingresar(ESTUDIANTE)
        reserva = self.reservar(estudiante).json
        self.assertEqual(self.cliente.post(
            f"/api/reservas/{reserva['id']}/confirmacion",
            headers=estudiante, json={}).status_code, 403)
        gestor = self.ingresar(GESTOR_DOCENTE)
        self.assertEqual(self.cliente.get("/api/reservas", headers=gestor).json["total"], 1)

    def test_valida_cuerpo_fecha_estado_y_transiciones(self):
        estudiante = self.ingresar(ESTUDIANTE)
        base = {"item_id": self.item_id("LIB-CLRS"),
                "modalidad_id": self.modalidad_id(EXTERNA),
                "fecha_inicio": "2026-10-20", "fecha_fin": "2026-10-26"}
        casos = [
            ({}, 400),
            ({**base, "item_id": "1"}, 400),
            ({**base, "fecha_inicio": "20-10-2026"}, 400),
            ({**base, "fecha_inicio": "2026-10-18"}, 422),
            ({**base, "fecha_inicio": "2027-10-20", "fecha_fin": "2027-10-21"}, 422),
            ({**base, "otro": True}, 400),
            ({**base, "rol_solicitante": 5}, 400),
            ({**base, "rol_solicitante": "DOCENTE"}, 422),
        ]
        for cuerpo, estado in casos:
            with self.subTest(cuerpo=cuerpo):
                self.assertEqual(self.cliente.post(
                    "/api/reservas", headers=estudiante, json=cuerpo).status_code, estado)
        self.assertEqual(self.cliente.get(
            "/api/reservas?estado=desconocido", headers=estudiante).status_code, 400)
        self.assertEqual(self.cliente.get(
            "/api/reservas?pagina=0", headers=estudiante).status_code, 400)
        self.assertEqual(self.cliente.get(
            "/api/reservas?otro=1", headers=estudiante).status_code, 400)

    def test_no_confirma_un_rango_que_se_superpone_con_un_prestamo(self):
        administrador = self.ingresar(ADMIN)
        self.entregar(administrador)
        reserva = self.reservar(
            self.ingresar(GESTOR_DOCENTE), fecha="2026-10-20",
            fecha_fin="2026-10-27")
        respuesta = reserva
        self.assertEqual(respuesta.status_code, 409)
        self.assertIn("ocupado hasta", respuesta.json["error"])
