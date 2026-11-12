"""Reportes PDF de acciones por usuario y por ítem."""

from datetime import date

from .ayudas import ADMIN, ESTUDIANTE, EXTERNA, GESTOR_DOCENTE, ApiBase

RANGO = "desde=2026-09-01&hasta=2026-10-31"


class ReportesBase(ApiBase):
    def _sembrar(self):
        self.estudiante = self.ingresar(ESTUDIANTE)
        gestor = self.ingresar(GESTOR_DOCENTE)
        self.estudiante_id = self.usuario_id(ESTUDIANTE, self.ingresar(ADMIN))
        self.item_reserva = self.item_id("LIB-CLRS")
        self.item_prestamo = self.item_id("LIB-GOF")
        modalidad = self.modalidad_id(EXTERNA)
        self.cliente.post("/api/reservas", headers=self.estudiante, json={
            "item_id": self.item_reserva, "modalidad_id": modalidad,
            "fecha_inicio": "2026-10-20", "fecha_fin": "2026-10-26"})
        self.cliente.post("/api/prestamos", headers=gestor, json={
            "usuario_id": self.estudiante_id, "item_ids": [self.item_prestamo],
            "modalidad_id": modalidad})
        self.cliente.post("/api/sanciones", headers=gestor, json={
            "usuario_id": self.estudiante_id, "origen": "DANO",
            "motivo": "Daño reportado en prueba", "dias": 3})
        return gestor


class ReportesPdfTest(ReportesBase):
    def test_reporte_de_usuario_propio_devuelve_pdf(self):
        self._sembrar()
        r = self.cliente.get(
            f"/api/reportes/usuario/{self.estudiante_id}?{RANGO}", headers=self.estudiante)
        self.assertEqual(r.status_code, 200, r.data[:200])
        self.assertEqual(r.content_type, "application/pdf")
        self.assertEqual(r.data[:5], b"%PDF-")
        self.assertIn("attachment", r.headers.get("Content-Disposition", ""))
        self.assertIn(".pdf", r.headers.get("Content-Disposition", ""))

    def test_reporte_de_item_como_gestor_devuelve_pdf(self):
        gestor = self._sembrar()
        r = self.cliente.get(
            f"/api/reportes/item/{self.item_prestamo}?{RANGO}", headers=gestor)
        self.assertEqual(r.status_code, 200, r.data[:200])
        self.assertEqual(r.content_type, "application/pdf")
        self.assertEqual(r.data[:5], b"%PDF-")

    def test_rango_mayor_a_90_dias_es_400(self):
        gestor = self._sembrar()
        r = self.cliente.get(
            f"/api/reportes/usuario/{self.estudiante_id}?desde=2026-01-01&hasta=2026-10-31",
            headers=gestor)
        self.assertEqual(r.status_code, 400)

    def test_fechas_faltantes_es_400(self):
        self._sembrar()
        self.assertEqual(self.cliente.get(
            f"/api/reportes/usuario/{self.estudiante_id}", headers=self.estudiante
        ).status_code, 400)

    def test_hasta_antes_de_desde_es_400(self):
        self._sembrar()
        self.assertEqual(self.cliente.get(
            f"/api/reportes/usuario/{self.estudiante_id}?desde=2026-10-31&hasta=2026-09-01",
            headers=self.estudiante).status_code, 400)

    def test_prestatario_no_genera_reporte_ajeno(self):
        self._sembrar()
        ajeno = self.usuario_id(GESTOR_DOCENTE, self.ingresar(ADMIN))
        self.assertEqual(self.cliente.get(
            f"/api/reportes/usuario/{ajeno}?{RANGO}", headers=self.estudiante
        ).status_code, 403)

    def test_prestatario_no_genera_reporte_de_item(self):
        self._sembrar()
        self.assertEqual(self.cliente.get(
            f"/api/reportes/item/{self.item_prestamo}?{RANGO}", headers=self.estudiante
        ).status_code, 403)

    def test_usuario_inexistente_es_404(self):
        gestor = self._sembrar()
        self.assertEqual(self.cliente.get(
            f"/api/reportes/usuario/999999?{RANGO}", headers=gestor).status_code, 404)

    def test_datos_incluyen_acciones_y_resumen(self):
        gestor = self._sembrar()
        servicios = self.app.extensions["servicios"]
        uid, version, espacio = servicios.tokens.verificar(
            gestor["Authorization"].split()[1])
        with self.app.app_context():
            actor = servicios.identidad.usuario_de_sesion(uid, version)
            servicios.identidad.activar_espacio(actor, espacio)
            datos = servicios.reportes.datos_usuario(
                actor, self.estudiante_id, date(2026, 9, 1), date(2026, 10, 31))
        resumen = datos["resumen"]
        self.assertEqual(resumen["prestamos_entregados"], 1)
        self.assertEqual(resumen["sanciones_aplicadas"], 1)
        self.assertGreaterEqual(resumen["reservas_solicitadas"], 1)
        self.assertEqual(resumen["total"], len(datos["acciones"]))
        self.assertTrue(all(a.categoria in ("RESERVA", "PRESTAMO", "SANCION")
                            for a in datos["acciones"]))
