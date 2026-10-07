"""Utilidades compartidas por las pruebas de la API."""

import unittest

from prestamos_academicos.web import create_app

CLAVE = "demo1234"
ADMIN = "admin@escuela.edu"
ESTUDIANTE = "jesus.perez@escuela.edu"
GESTOR_DOCENTE = "luis.ramos@escuela.edu"


class ApiBase(unittest.TestCase):
    datos_demo = True

    def setUp(self):
        self.app = create_app("sqlite+pysqlite:///:memory:", datos_demo=self.datos_demo,
                              secret_key="prueba")
        self.cliente = self.app.test_client()

    def ingresar(self, correo=ADMIN, password=CLAVE):
        r = self.cliente.post("/api/auth/login", json={"correo": correo, "password": password})
        self.assertEqual(r.status_code, 200, r.json)
        return {"Authorization": f"Bearer {r.json['token']}"}

    def usuario_id(self, correo, cabeceras=None):
        cabeceras = cabeceras or self.ingresar()
        lista = self.cliente.get("/api/usuarios", headers=cabeceras).json
        return next(u["id"] for u in lista if u["correo"] == correo)

    def item_id(self, codigo):
        lista = self.cliente.get("/api/items?limite=100").json["items"]
        return next(i["id"] for i in lista if i["codigo"] == codigo)
