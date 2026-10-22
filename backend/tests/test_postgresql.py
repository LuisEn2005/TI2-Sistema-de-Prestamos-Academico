"""Prueba de integración que CI ejecuta contra PostgreSQL real."""

import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from prestamos_academicos.web import create_app


URL = os.environ.get("TEST_POSTGRES_URL")


@unittest.skipUnless(URL, "TEST_POSTGRES_URL no está configurada")
class PostgreSQLIntegracionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        url = make_url(URL)
        if url.get_backend_name() != "postgresql" or not (url.database or "").endswith("_test"):
            raise RuntimeError("TEST_POSTGRES_URL debe apuntar a una base PostgreSQL terminada en _test.")
        motor = create_engine(URL)
        with motor.begin() as conexion:
            conexion.execute(text("DROP SCHEMA public CASCADE"))
            conexion.execute(text("CREATE SCHEMA public"))
        motor.dispose()

    def test_migraciones_y_recorrido_principal(self):
        with patch.dict(os.environ, {
            "ADMIN_CORREO": "admin-ci@escuela.edu",
            "ADMIN_PASSWORD": "clave-ci-segura",
        }):
            app = create_app(URL, datos_demo=False, secret_key="ci")
        cliente = app.test_client()

        acceso = cliente.post("/api/auth/login", json={
            "correo": "admin-ci@escuela.edu", "password": "clave-ci-segura"})
        self.assertEqual(acceso.status_code, 200, acceso.json)
        self.assertEqual(acceso.json["usuario"]["roles"], ["ADMINISTRADOR_SISTEMA"])
        cabeceras = {"Authorization": f"Bearer {acceso.json['token']}"}

        usuario = cliente.post("/api/usuarios", headers=cabeceras, json={
            "nombre": "Estudiante CI", "correo": "estudiante-ci@escuela.edu",
            "perfiles": {"ESTUDIANTE": {"codigo_estudiante": "EST-CI-001"}},
        })
        self.assertEqual(usuario.status_code, 201, usuario.json)
        item = cliente.post("/api/items", headers=cabeceras, json={
            "tipo": "LIBRO", "codigo": "lib-ci", "nombre": "Libro CI",
            "categoria": "Pruebas", "atributos": {
                "isbn": "978-0000000002", "autor": "Autor CI", "editorial": "Editorial CI"},
        })
        self.assertEqual(item.status_code, 201, item.json)
        self.assertEqual(item.json["codigo"], "LIB-CI")

        modalidades = cliente.get("/api/modalidades", headers=cabeceras).json
        externa = next(m for m in modalidades if m["nombre"].startswith("Externa"))
        segundo = cliente.post("/api/items", headers=cabeceras, json={
            "tipo": "LIBRO", "codigo": "lib-ci-2", "nombre": "Libro CI 2",
            "categoria": "Pruebas", "atributos": {"isbn": "978-0000000004", "autor": "Autor CI"}})
        prestamo = cliente.post("/api/prestamos", headers=cabeceras, json={
            "usuario_id": usuario.json["id"], "modalidad_id": externa["id"],
            "item_ids": [item.json["id"], segundo.json["id"]]})
        self.assertEqual(prestamo.status_code, 201, prestamo.json)
        self.assertEqual(len(prestamo.json["items"]), 2)
        self.assertIsNotNone(prestamo.json["fecha_limite"])
        repetido = cliente.post("/api/prestamos", headers=cabeceras, json={
            "usuario_id": usuario.json["id"], "modalidad_id": externa["id"],
            "item_ids": [item.json["id"]]})
        self.assertEqual(repetido.status_code, 409)
        devolucion = cliente.post(
            f"/api/prestamos/{prestamo.json['id']}/devolucion", headers=cabeceras, json={
                "condiciones": [
                    {"item_id": item.json["id"], "condicion": "BUEN_ESTADO"},
                    {"item_id": segundo.json["id"], "condicion": "DANADO"}]})
        self.assertEqual(devolucion.status_code, 200, devolucion.json)
        self.assertEqual(cliente.get(f"/api/items/{segundo.json['id']}").json["estado"],
                         "EN_MANTENIMIENTO")
        self.assertEqual(cliente.get(f"/api/items/{item.json['id']}").json["estado"],
                         "DISPONIBLE")

        motor = create_engine(URL)
        with motor.connect() as conexion:
            self.assertEqual(conexion.execute(text(
                "SELECT version_num FROM alembic_version")).scalar_one(), "0007")
        motor.dispose()
