"""Historial unificado de préstamos, reservas y sanciones (RF17)."""

from .ayudas import ADMIN, ESTUDIANTE, EXTERNA, GESTOR_DOCENTE, ApiBase


class HistorialBase(ApiBase):
    def _sembrar(self):
        """Genera una reserva, un préstamo y una sanción para el estudiante."""
        estudiante = self.ingresar(ESTUDIANTE)
        gestor = self.ingresar(GESTOR_DOCENTE)
        self.estudiante_id = self.usuario_id(ESTUDIANTE, self.ingresar(ADMIN))
        self.item_reserva = self.item_id("LIB-CLRS")
        self.item_prestamo = self.item_id("LIB-GOF")

        reserva = self.cliente.post("/api/reservas", headers=estudiante, json={
            "item_id": self.item_reserva, "modalidad_id": self.modalidad_id(EXTERNA),
            "fecha_inicio": "2026-10-20", "fecha_fin": "2026-10-26"})
        self.assertEqual(reserva.status_code, 201, reserva.json)

        prestamo = self.cliente.post("/api/prestamos", headers=gestor, json={
            "usuario_id": self.estudiante_id, "item_ids": [self.item_prestamo],
            "modalidad_id": self.modalidad_id(EXTERNA)})
        self.assertEqual(prestamo.status_code, 201, prestamo.json)

        sancion = self.cliente.post("/api/sanciones", headers=gestor, json={
            "usuario_id": self.estudiante_id, "origen": "DANO",
            "motivo": "Daño reportado en prueba", "dias": 3})
        self.assertEqual(sancion.status_code, 201, sancion.json)
        return estudiante, gestor

    def historial(self, cabeceras, **filtros):
        r = self.cliente.get("/api/historial", headers=cabeceras, query_string=filtros)
        self.assertEqual(r.status_code, 200, r.json)
        return r.json


class HistorialUnificadoTest(HistorialBase):
    def test_titular_ve_sus_tres_tipos_de_movimiento(self):
        estudiante, _ = self._sembrar()
        datos = self.historial(estudiante)
        self.assertEqual(datos["total"], 3, datos)
        tipos = {m["tipo"] for m in datos["movimientos"]}
        self.assertEqual(tipos, {"PRESTAMO", "RESERVA", "SANCION"})
        self.assertTrue(all(m["usuario_id"] == self.estudiante_id
                            for m in datos["movimientos"]))

    def test_orden_descendente_por_fecha(self):
        estudiante, _ = self._sembrar()
        fechas = [m["fecha"] for m in self.historial(estudiante)["movimientos"]]
        self.assertEqual(fechas, sorted(fechas, reverse=True))

    def test_filtro_por_tipo(self):
        estudiante, _ = self._sembrar()
        datos = self.historial(estudiante, tipo="RESERVA")
        self.assertEqual(datos["total"], 1)
        self.assertEqual(datos["movimientos"][0]["tipo"], "RESERVA")
        self.assertEqual(datos["movimientos"][0]["item_id"], self.item_reserva)

    def test_tipo_invalido_es_400(self):
        estudiante = self.ingresar(ESTUDIANTE)
        self.assertEqual(
            self.cliente.get("/api/historial?tipo=OTRO", headers=estudiante).status_code,
            400)

    def test_filtro_por_item_excluye_sanciones(self):
        estudiante, _ = self._sembrar()
        datos = self.historial(estudiante, item_id=self.item_prestamo)
        self.assertEqual(datos["total"], 1)
        self.assertEqual(datos["movimientos"][0]["tipo"], "PRESTAMO")
        self.assertTrue(all(m["tipo"] != "SANCION" for m in datos["movimientos"]))

    def test_filtro_por_rango_de_fechas(self):
        estudiante, _ = self._sembrar()
        # La reserva se solicitó el 2026-10-19; acotar a días posteriores la excluye.
        datos = self.historial(estudiante, desde="2026-10-20")
        self.assertTrue(all(m["fecha"] >= "2026-10-20" for m in datos["movimientos"]))
        self.assertNotIn("RESERVA", {m["tipo"] for m in datos["movimientos"]})

    def test_titular_ignora_filtro_de_usuario_ajeno(self):
        estudiante, _ = self._sembrar()
        ajeno = self.usuario_id(ADMIN, self.ingresar(ADMIN))
        # Sin permiso global, el filtro usuario_id no deja espiar a otros.
        datos = self.historial(estudiante, usuario_id=ajeno)
        self.assertEqual(datos["total"], 3)
        self.assertTrue(all(m["usuario_id"] == self.estudiante_id
                            for m in datos["movimientos"]))

    def test_rol_global_filtra_por_usuario(self):
        self._sembrar()
        admin = self.ingresar(ADMIN)
        datos = self.historial(admin, usuario_id=self.estudiante_id)
        self.assertEqual(datos["total"], 3)
        self.assertTrue(all(m["usuario_id"] == self.estudiante_id
                            for m in datos["movimientos"]))

    def test_requiere_autenticacion(self):
        self.assertEqual(self.cliente.get("/api/historial").status_code, 401)
