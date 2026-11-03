"""Calendario, rangos y cupo compartido."""

from datetime import timedelta

from .ayudas import ADMIN, ESTUDIANTE, EXTERNA, GESTOR_DOCENTE, ApiBase


class CalendarioRangosTest(ApiBase):
    def _reserva(self, headers, codigo, inicio, fin, modalidad=EXTERNA):
        return self.cliente.post("/api/reservas", headers=headers, json={
            "item_id": self.item_id(codigo),
            "modalidad_id": self.modalidad_id(modalidad),
            "fecha_inicio": inicio,
            "fecha_fin": fin,
        })

    def _prestamo(self, headers, codigo="LIB-CLRS", correo=ESTUDIANTE,
                  fin="2026-10-26"):
        return self.cliente.post("/api/prestamos", headers=headers, json={
            "usuario_id": self.usuario_id(correo, headers),
            "item_ids": [self.item_id(codigo)],
            "modalidad_id": self.modalidad_id(EXTERNA),
            "fecha_fin": fin,
        })

    def test_varias_solicitudes_compiten_y_el_gestor_elige(self):
        estudiante = self.ingresar(ESTUDIANTE)
        primera = self._reserva(
            estudiante, "LIB-CLRS", "2026-10-20", "2026-10-26")
        docente = self._reserva(
            self.ingresar(GESTOR_DOCENTE, espacio="PERSONAL"),
            "LIB-CLRS", "2026-10-22", "2026-10-29")
        self.assertEqual((primera.status_code, docente.status_code), (201, 201))

        admin = self.ingresar(ADMIN, espacio="INVENTARIO")
        confirmada = self.cliente.post(
            f"/api/reservas/{docente.json['id']}/confirmacion", headers=admin, json={})
        self.assertEqual(confirmada.status_code, 200, confirmada.json)
        reservas = self.cliente.get(
            "/api/reservas?historial=1", headers=admin).json["reservas"]
        estados = {r["id"]: r["estado"] for r in reservas}
        self.assertEqual(estados[docente.json["id"]], "CONFIRMADA")
        self.assertEqual(estados[primera.json["id"]], "RECHAZADA")

    def test_calendario_publico_oculta_solicitantes(self):
        estudiante = self.ingresar(ESTUDIANTE)
        reserva = self._reserva(
            estudiante, "LIB-CLRS", "2026-10-20", "2026-10-26").json
        admin = self.ingresar(ADMIN, espacio="INVENTARIO")
        solicitudes = self.cliente.get(
            "/api/reservas/calendario", headers=admin,
            query_string={"item_id": self.item_id("LIB-CLRS"),
                          "desde": "2026-10-19", "hasta": "2026-10-31"})
        self.assertEqual(solicitudes.status_code, 200, solicitudes.json)
        self.assertEqual(solicitudes.json[0]["usuario"], "Jesus Perez")

        publico = self.cliente.get(
            f"/api/items/{self.item_id('LIB-CLRS')}/calendario",
            query_string={"desde": "2026-10-19", "hasta": "2026-10-25"})
        self.assertEqual(publico.status_code, 200, publico.json)
        self.assertNotIn("usuario", str(publico.json))
        self.assertEqual(next(d["estado"] for d in publico.json["dias"]
                              if d["fecha"] == "2026-10-24"), "NO_DISPONIBLE")

        self.cliente.post(
            f"/api/reservas/{reserva['id']}/confirmacion", headers=admin, json={})
        publico = self.cliente.get(
            f"/api/items/{self.item_id('LIB-CLRS')}/calendario",
            query_string={"desde": "2026-10-19", "hasta": "2026-10-25"}).json
        self.assertEqual(next(d["estado"] for d in publico["dias"]
                              if d["fecha"] == "2026-10-20"), "RESERVADO")

    def test_cupo_es_compartido_entre_prestamos_y_reservas(self):
        estudiante = self.ingresar(ESTUDIANTE)
        for codigo in ("LIB-CLRS", "LIB-CLEAN"):
            respuesta = self._reserva(
                estudiante, codigo, "2026-10-20", "2026-10-26")
            self.assertEqual(respuesta.status_code, 201, respuesta.json)
        admin = self.ingresar(ADMIN, espacio="INVENTARIO")
        primero = self._prestamo(admin, "EQ-META")
        self.assertEqual(primero.status_code, 201, primero.json)
        creado = self.cliente.post("/api/items", headers=admin, json={
            "tipo": "LIBRO", "codigo": "LIB-CUPO", "nombre": "Libro de cupo",
            "categoria": "Pruebas", "atributos": {"isbn": "C-1", "autor": "Prueba"},
        })
        self.assertEqual(creado.status_code, 201, creado.json)
        segundo = self._prestamo(admin, "LIB-CUPO")
        self.assertEqual(segundo.status_code, 422, segundo.json)
        self.assertIn("2 reservados", segundo.json["error"])

    def test_cierre_aplaza_devolucion_y_evitar_sancion(self):
        inventario = self.ingresar(ADMIN, espacio="INVENTARIO")
        admin = self.ingresar(ADMIN)
        prestamo = self._prestamo(inventario).json
        cierre = self.cliente.post("/api/dias-no-laborables", headers=admin, json={
            "fecha_inicio": "2026-10-26", "fecha_fin": "2026-10-26",
            "tipo": "FERIADO", "motivo": "Aniversario institucional",
        })
        self.assertEqual(cierre.status_code, 201, cierre.json)
        actualizado = self.cliente.get(
            f"/api/prestamos/{prestamo['id']}", headers=inventario).json
        self.assertEqual(actualizado["fecha_limite"], "2026-10-27")
        self.assertEqual(actualizado["aplazamientos"][0]["fecha_anterior"], "2026-10-26")

        self.reloj.instante += timedelta(days=8)
        item = actualizado["items"][0]
        devuelto = self.cliente.post(
            f"/api/prestamos/{prestamo['id']}/devolucion", headers=inventario,
            json={"condiciones": [{"item_id": item["item_id"],
                                    "condicion": "BUEN_ESTADO"}]})
        self.assertEqual(devuelto.status_code, 200, devuelto.json)
        self.assertEqual(devuelto.json["dias_atraso"], 0)
        self.assertNotIn("sancion_generada_id", devuelto.json)

    def test_docente_y_administrativo_tienen_catorce_dias(self):
        admin = self.ingresar(ADMIN, espacio="INVENTARIO")
        condiciones = self.cliente.get("/api/prestamos/condiciones", headers=admin,
            query_string={"usuario_id": self.usuario_id(GESTOR_DOCENTE, admin),
                          "modalidad_id": self.modalidad_id(EXTERNA)}).json
        self.assertEqual((condiciones["dias_plazo"], condiciones["fecha_limite"]),
                         (14, "2026-11-02"))

    def test_fin_de_semana_no_admite_entrega(self):
        self.reloj.instante += timedelta(days=5)  # sábado 24 de octubre
        respuesta = self._prestamo(
            self.ingresar(ADMIN, espacio="INVENTARIO"), fin="2026-10-31")
        self.assertEqual(respuesta.status_code, 422, respuesta.json)
        self.assertIn("fecha de entrega no es laborable", respuesta.json["error"])

    def test_cierre_reprograma_inicio_y_conserva_el_final(self):
        estudiante = self.ingresar(ESTUDIANTE)
        reserva = self._reserva(
            estudiante, "LIB-CLRS", "2026-10-26", "2026-11-02").json
        inventario = self.ingresar(ADMIN, espacio="INVENTARIO")
        admin = self.ingresar(ADMIN)
        confirmada = self.cliente.post(
            f"/api/reservas/{reserva['id']}/confirmacion", headers=inventario, json={})
        self.assertEqual(confirmada.status_code, 200, confirmada.json)

        cierre = self.cliente.post("/api/dias-no-laborables", headers=admin, json={
            "fecha_inicio": "2026-10-26", "fecha_fin": "2026-10-26",
            "tipo": "HUELGA", "motivo": "Suspensión de actividades",
        })
        self.assertEqual(cierre.status_code, 201, cierre.json)
        actualizada = self.cliente.get(
            "/api/reservas", headers=inventario).json["reservas"][0]
        self.assertEqual(
            (actualizada["fecha_inicio"], actualizada["fecha_fin"]),
            ("2026-10-27", "2026-11-02"))

    def test_no_permite_reservar_el_mismo_item_en_rangos_superpuestos(self):
        estudiante = self.ingresar(ESTUDIANTE)
        primera = self._reserva(
            estudiante, "LIB-CLRS", "2026-10-20", "2026-10-23")
        duplicada = self._reserva(
            estudiante, "LIB-CLRS", "2026-10-22", "2026-10-26")
        consecutiva = self._reserva(
            estudiante, "LIB-CLRS", "2026-10-26", "2026-10-27")
        self.assertEqual(primera.status_code, 201)
        self.assertEqual(duplicada.status_code, 409)
        self.assertEqual(consecutiva.status_code, 201, consecutiva.json)

    def test_inventario_protegido_muestra_reserva_y_usuario_por_fecha(self):
        estudiante = self.ingresar(ESTUDIANTE)
        reserva = self._reserva(
            estudiante, "LIB-CLRS", "2026-10-20", "2026-10-26").json
        admin = self.ingresar(ADMIN, espacio="INVENTARIO")
        self.cliente.post(
            f"/api/reservas/{reserva['id']}/confirmacion", headers=admin, json={})
        vista = self.cliente.get(
            "/api/inventario", headers=admin,
            query_string={"fecha": "2026-10-21", "estado": "RESERVADO"})
        self.assertEqual(vista.status_code, 200, vista.json)
        item = next(i for i in vista.json["items"] if i["codigo"] == "LIB-CLRS")
        self.assertEqual(item["asignacion"]["usuario"], "Jesus Perez")
        self.assertEqual(self.cliente.get(
            "/api/inventario?fecha=2026-10-21", headers=estudiante).status_code, 403)

    def test_solo_administrador_gestiona_y_puede_editar_cierres(self):
        estudiante = self.ingresar(ESTUDIANTE)
        cuerpo = {
            "fecha_inicio": "2026-11-04", "fecha_fin": "2026-11-04",
            "tipo": "OTRO", "motivo": "Mantenimiento institucional",
        }
        self.assertEqual(self.cliente.post(
            "/api/dias-no-laborables", headers=estudiante, json=cuerpo).status_code, 403)

        admin = self.ingresar(ADMIN)
        creada = self.cliente.post(
            "/api/dias-no-laborables", headers=admin, json=cuerpo).json
        editada = self.cliente.patch(
            f"/api/dias-no-laborables/{creada['id']}", headers=admin,
            json={"fecha_inicio": "2026-11-05", "fecha_fin": "2026-11-05",
                  "tipo": "FERIADO", "motivo": "Aniversario"})
        self.assertEqual(editada.status_code, 200, editada.json)
        self.assertEqual(
            (editada.json["fecha_inicio"], editada.json["tipo"], editada.json["motivo"]),
            ("2026-11-05", "FERIADO", "Aniversario"))

    def test_reserva_rechaza_fin_de_semana_y_sugiere_fecha_laborable(self):
        respuesta = self._reserva(
            self.ingresar(ESTUDIANTE), "LIB-CLRS", "2026-10-24", "2026-10-26")
        self.assertEqual(respuesta.status_code, 422, respuesta.json)
        self.assertIn("Siguiente fecha permitida: 2026-10-26", respuesta.json["error"])

    def test_reserva_rechaza_el_mismo_dia_y_prestamo_respeta_pendientes(self):
        estudiante = self.ingresar(ESTUDIANTE)
        mismo_dia = self._reserva(
            estudiante, "LIB-CLRS", "2026-10-19", "2026-10-20")
        self.assertEqual(mismo_dia.status_code, 422)
        pendiente = self._reserva(
            estudiante, "LIB-CLRS", "2026-10-20", "2026-10-26")
        self.assertEqual(pendiente.status_code, 201, pendiente.json)
        directo = self._prestamo(
            self.ingresar(ADMIN, espacio="INVENTARIO"), "LIB-CLRS")
        self.assertEqual(directo.status_code, 409)
        self.assertIn("solicitudes pendientes", directo.json["error"])

    def test_cierre_desplaza_reservas_confirmadas_sin_reutilizar_el_mismo_dia(self):
        estudiante = self.ingresar(ESTUDIANTE)
        inventario = self.ingresar(ADMIN, espacio="INVENTARIO")
        admin = self.ingresar(ADMIN)
        primera = self._reserva(
            estudiante, "LIB-CLRS", "2026-11-09", "2026-11-13").json
        self.cliente.post(
            f"/api/reservas/{primera['id']}/confirmacion", headers=inventario, json={})
        segunda = self._reserva(
            self.ingresar(GESTOR_DOCENTE, espacio="PERSONAL"),
            "LIB-CLRS", "2026-11-16", "2026-11-18").json
        self.cliente.post(
            f"/api/reservas/{segunda['id']}/confirmacion", headers=inventario, json={})
        cierre = self.cliente.post("/api/dias-no-laborables", headers=admin, json={
            "fecha_inicio": "2026-11-13", "fecha_fin": "2026-11-13",
            "tipo": "FERIADO", "motivo": "Cierre extraordinario",
        })
        self.assertEqual(cierre.status_code, 201, cierre.json)
        reservas = self.cliente.get(
            "/api/reservas?historial=1", headers=inventario).json["reservas"]
        por_id = {r["id"]: r for r in reservas}
        self.assertEqual(
            (por_id[primera["id"]]["fecha_fin"],
             por_id[segunda["id"]]["fecha_inicio"],
             por_id[segunda["id"]]["fecha_fin"]),
            ("2026-11-16", "2026-11-17", "2026-11-18"))
