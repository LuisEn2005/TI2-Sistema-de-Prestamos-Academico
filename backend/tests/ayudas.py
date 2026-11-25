"""Utilidades compartidas por las pruebas de la API."""

import unittest
from datetime import datetime, timezone

from prestamos_academicos.compartido.reloj import Reloj
from prestamos_academicos.web import create_app

CLAVE = "demo1234"
ADMIN = "admin@escuela.edu"
ESTUDIANTE = "jesus.perez@escuela.edu"
GESTOR = "luis.ramos@escuela.edu"
GESTOR_2 = "lorenzo.quispe@escuela.edu"
DOCENTE = "yessenia.yari@escuela.edu"
IN_SITU = "In situ (en sala)"
EXTERNA = "Externa (a domicilio)"


class RelojFijo(Reloj):
    """Reloj controlable: permite probar plazos y atrasos sin esperar días reales."""

    def __init__(self, instante):
        super().__init__("America/Lima")
        self.instante = instante

    def ahora(self):
        return self.instante


class ApiBase(unittest.TestCase):
    datos_demo = True
    # 19-oct-2026 15:00 en Lima (UTC-5): mediodía, lejos de cualquier cambio de día.
    instante_inicial = datetime(2026, 10, 19, 20, 0, tzinfo=timezone.utc)

    def setUp(self):
        self.reloj = RelojFijo(self.instante_inicial)
        self.app = create_app("sqlite+pysqlite:///:memory:", datos_demo=self.datos_demo,
                              secret_key="prueba", reloj=self.reloj)
        self.cliente = self.app.test_client()

    def ingresar(self, correo=ADMIN, password=CLAVE, espacio=None):
        if espacio is None:
            espacio = {
                ADMIN: "ADMINISTRACION",
                ESTUDIANTE: "PERSONAL",
                GESTOR: "INVENTARIO",
            }.get(correo)
        cuerpo = {"correo": correo, "password": password}
        if espacio:
            cuerpo["espacio"] = espacio
        r = self.cliente.post("/api/auth/login", json=cuerpo)
        self.assertEqual(r.status_code, 200, r.json)
        return {"Authorization": f"Bearer {r.json['token']}"}

    def usuario_id(self, correo, cabeceras=None):
        cabeceras = cabeceras or self.ingresar()
        respuesta = self.cliente.get("/api/usuarios", headers=cabeceras)
        if respuesta.status_code == 403:
            respuesta = self.cliente.get("/api/usuarios/prestatarios", headers=cabeceras)
        self.assertEqual(respuesta.status_code, 200, respuesta.json)
        lista = respuesta.json
        return next(u["id"] for u in lista if u["correo"] == correo)

    def item_id(self, codigo):
        lista = self.cliente.get("/api/items?limite=100").json["items"]
        return next(i["id"] for i in lista if i["codigo"] == codigo)

    def modalidad_id(self, nombre=EXTERNA):
        h = self.ingresar()
        return next(m["id"] for m in self.cliente.get("/api/modalidades", headers=h).json
                    if m["nombre"] == nombre)

    def incidencia(self, gestor, codigo, condicion="DANADO", correo=ESTUDIANTE):
        """Presta `codigo` y lo recibe dañado o perdido; devuelve lo que pide una sanción manual."""
        prestamo = self.cliente.post("/api/prestamos", headers=gestor, json={
            "usuario_id": self.usuario_id(correo), "item_ids": [self.item_id(codigo)],
            "modalidad_id": self.modalidad_id(EXTERNA)})
        self.assertEqual(prestamo.status_code, 201, prestamo.json)
        return self.recibir(gestor, prestamo.json["id"], self.item_id(codigo), condicion)

    def recibir(self, gestor, prestamo_id, item_id, condicion="DANADO"):
        r = self.cliente.post(f"/api/prestamos/{prestamo_id}/devolucion", headers=gestor,
                              json={"condiciones": [{"item_id": item_id, "condicion": condicion}]})
        self.assertEqual(r.status_code, 200, r.json)
        return {"prestamo_id": prestamo_id, "item_id": item_id}

    def estado_item(self, codigo):
        return self.cliente.get(f"/api/items/{self.item_id(codigo)}").json["estado"]
