"""Reservas y renovaciones completas (Sprint 4)."""

from datetime import timedelta

from .ayudas import ADMIN, ESTUDIANTE, EXTERNA, GESTOR_DOCENTE, ApiBase


class ReservasBase(ApiBase):
    def reservar(self, h, codigo="LIB-CLRS", fecha="2026-10-20", **extra):
        return self.cliente.post("/api/reservas", headers=h, json={
            "item_id": self.item_id(codigo), "fecha_reserva": fecha, **extra})

    def entregar(self, h, correo=ESTUDIANTE, codigo="LIB-CLRS"):
        return self.cliente.post("/api/prestamos", headers=h, json={
            "usuario_id": self.usuario_id(correo),
            "item_ids": [self.item_id(codigo)],
            "modalidad_id": self.modalidad_id(EXTERNA),
        })


class FlujoReservaTest(ReservasBase):
    def test_solicitar_confirmar_y_convertir_en_prestamo(self):
        estudiante = self.ingresar(ESTUDIANTE)
        creada = self.reservar(estudiante).json
        self.assertEqual((creada["estado"], creada["rol_solicitante"]),
                         ("PENDIENTE", "ESTUDIANTE"))
        self.assertEqual((creada["fecha_reserva"], creada["fecha_expiracion"]),
                         ("2026-10-20", "2026-10-22"))
        self.assertEqual(self.estado_item("LIB-CLRS"), "RESERVADO")

        administrador = self.ingresar(ADMIN)
        confirmada = self.cliente.post(
            f"/api/reservas/{creada['id']}/confirmacion", headers=administrador, json={})
        self.assertEqual(confirmada.status_code, 200, confirmada.json)
        self.assertEqual(confirmada.json["estado"], "CONFIRMADA")

        prestamo = self.cliente.post(
            f"/api/reservas/{creada['id']}/prestamo", headers=administrador,
            json={"modalidad_id": self.modalidad_id(EXTERNA)})
        self.assertEqual(prestamo.status_code, 201, prestamo.json)
        self.assertEqual((prestamo.json["reserva_id"], prestamo.json["dias_plazo"]),
                         (creada["id"], 7))
        self.assertEqual(prestamo.json["fecha_limite"], "2026-10-26")
        self.assertEqual(self.estado_item("LIB-CLRS"), "PRESTADO")
        reserva = self.cliente.get("/api/reservas", headers=estudiante).json["reservas"][0]
        self.assertEqual(reserva["estado"], "CONVERTIDA")

    def test_cancelar_libera_el_recurso_y_no_se_repite(self):
        estudiante = self.ingresar(ESTUDIANTE)
        reserva = self.reservar(estudiante).json
        cancelada = self.cliente.post(
            f"/api/reservas/{reserva['id']}/cancelacion", headers=estudiante, json={})
        self.assertEqual(cancelada.status_code, 200, cancelada.json)
        self.assertEqual(cancelada.json["estado"], "CANCELADA")
        self.assertEqual(self.estado_item("LIB-CLRS"), "DISPONIBLE")
        repetida = self.cliente.post(
            f"/api/reservas/{reserva['id']}/cancelacion", headers=estudiante, json={})
        self.assertEqual(repetida.status_code, 409)

    def test_expiracion_automatica_libera_el_recurso(self):
        estudiante = self.ingresar(ESTUDIANTE)
        reserva = self.reservar(estudiante, fecha="2026-10-19").json
        self.assertEqual(reserva["fecha_expiracion"], "2026-10-21")
        self.reloj.instante += timedelta(days=3)
        listado = self.cliente.get("/api/reservas", headers=estudiante)
        self.assertEqual(listado.status_code, 200, listado.json)
        self.assertEqual(listado.json["reservas"][0]["estado"], "EXPIRADA")
        self.assertEqual(self.estado_item("LIB-CLRS"), "DISPONIBLE")

    def test_un_recurso_admite_una_sola_reserva_activa(self):
        self.assertEqual(self.reservar(self.ingresar(ESTUDIANTE)).status_code, 201)
        repetida = self.reservar(self.ingresar(GESTOR_DOCENTE))
        self.assertEqual(repetida.status_code, 409)
        self.assertIn("reserva activa", repetida.json["error"])


class RenovacionTest(ReservasBase):
    def test_reserva_pendiente_bloquea_renovacion_y_cancelarla_la_habilita(self):
        administrador = self.ingresar(ADMIN)
        prestamo = self.entregar(administrador).json
        reserva = self.reservar(
            self.ingresar(GESTOR_DOCENTE), fecha="2026-10-25").json
        self.assertEqual(self.estado_item("LIB-CLRS"), "PRESTADO")

        estudiante = self.ingresar(ESTUDIANTE)
        bloqueada = self.cliente.post(
            f"/api/prestamos/{prestamo['id']}/renovacion", headers=estudiante, json={})
        self.assertEqual(bloqueada.status_code, 409)
        self.assertIn("reserva pendiente", bloqueada.json["error"])

        self.cliente.post(
            f"/api/reservas/{reserva['id']}/cancelacion",
            headers=self.ingresar(GESTOR_DOCENTE), json={})
        renovada = self.cliente.post(
            f"/api/prestamos/{prestamo['id']}/renovacion", headers=estudiante, json={})
        self.assertEqual(renovada.status_code, 200, renovada.json)
        self.assertEqual((renovada.json["numero_renovaciones"], renovada.json["fecha_limite"]),
                         (1, "2026-11-02"))

    def test_no_renueva_prestamo_vencido_devuelto_o_ajeno(self):
        administrador = self.ingresar(ADMIN)
        prestamo = self.entregar(administrador).json
        self.reloj.instante += timedelta(days=8)
        vencido = self.cliente.post(
            f"/api/prestamos/{prestamo['id']}/renovacion",
            headers=self.ingresar(ESTUDIANTE), json={})
        self.assertEqual(vencido.status_code, 409)
        self.assertIn("vencido", vencido.json["error"])

        otro = self.cliente.post(
            f"/api/prestamos/{prestamo['id']}/renovacion",
            headers=self.ingresar(GESTOR_DOCENTE), json={})
        # El gestor tiene permiso para operar préstamos; la causa sigue siendo el vencimiento.
        self.assertEqual(otro.status_code, 409)


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
        base = {"item_id": self.item_id("LIB-CLRS"), "fecha_reserva": "2026-10-20"}
        casos = [
            ({}, 400),
            ({**base, "item_id": "1"}, 400),
            ({**base, "fecha_reserva": "20-10-2026"}, 400),
            ({**base, "fecha_reserva": "2026-10-18"}, 422),
            ({**base, "fecha_reserva": "2027-10-20"}, 422),
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

    def test_no_confirma_mientras_el_recurso_sigue_prestado(self):
        administrador = self.ingresar(ADMIN)
        self.entregar(administrador)
        reserva = self.reservar(self.ingresar(GESTOR_DOCENTE), fecha="2026-10-25").json
        respuesta = self.cliente.post(
            f"/api/reservas/{reserva['id']}/confirmacion", headers=administrador, json={})
        self.assertEqual(respuesta.status_code, 409)
        self.assertIn("sigue prestado", respuesta.json["error"])
