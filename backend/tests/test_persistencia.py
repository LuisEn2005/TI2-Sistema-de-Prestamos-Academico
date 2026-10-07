"""Migraciones y persistencia entre reinicios."""

import os
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from prestamos_academicos.web import create_app

from .ayudas import CLAVE


def crear_base_del_sprint_1(ruta):
    """Esquema exacto del MVP original, con datos de la primera demostración."""
    con = sqlite3.connect(ruta)
    con.executescript("""
        CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nombre VARCHAR(120) NOT NULL);
        CREATE TABLE recursos (id INTEGER PRIMARY KEY, codigo VARCHAR(30) NOT NULL UNIQUE,
            nombre VARCHAR(120) NOT NULL, tipo VARCHAR(30) NOT NULL,
            disponible BOOLEAN NOT NULL DEFAULT 1);
        CREATE TABLE prestamos (id INTEGER PRIMARY KEY,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
            recurso_id INTEGER NOT NULL REFERENCES recursos(id),
            fecha_prestamo DATETIME NOT NULL, fecha_devolucion DATETIME);
        INSERT INTO usuarios VALUES (1,'Ana Torres'),(2,'Luis Rivera');
        INSERT INTO recursos VALUES (1,'LIB-CLRS','Introduction to Algorithms (CLRS)','Libro',0),
            (2,'EQ-META','Meta Quest','Equipo',1);
        INSERT INTO prestamos VALUES (1,1,1,'2026-03-02 10:00:00',NULL);
    """)
    con.commit()
    con.close()


class MigracionTest(unittest.TestCase):
    def test_actualiza_una_base_del_sprint_1_conservando_los_datos(self):
        with TemporaryDirectory() as d:
            ruta = Path(d) / "mvp.sqlite"
            crear_base_del_sprint_1(ruta)
            app = create_app(f"sqlite:///{ruta}", datos_demo=True, secret_key="k")
            c = app.test_client()

            token = c.post("/api/auth/login", json={
                "correo": "admin@escuela.edu", "password": CLAVE}).json["token"]
            h = {"Authorization": f"Bearer {token}"}

            usuarios = c.get("/api/usuarios", headers=h).json
            nombres = {u["nombre"] for u in usuarios}
            self.assertIn("Jesus Perez", nombres)
            self.assertIn("Luis Ramos", nombres)
            heredado = next(u for u in usuarios if u["nombre"] == "Jesus Perez")
            self.assertEqual(heredado["roles"], ["ESTUDIANTE"])
            self.assertIsNotNone(heredado["perfiles"]["ESTUDIANTE"]["politica_servicio_id"])
            self.assertTrue(heredado["correo"].endswith("@sin-correo.local"))
            self.assertEqual(
                c.post("/api/auth/login", json={"correo": heredado["correo"],
                                                "password": CLAVE}).status_code, 401)

            items = {i["codigo"]: i for i in c.get("/api/items").json["items"]}
            self.assertEqual(items["LIB-CLRS"]["estado"], "PRESTADO")
            self.assertEqual(items["LIB-CLRS"]["tipo"], "LIBRO")
            self.assertEqual(items["EQ-META"]["estado"], "DISPONIBLE")

            prestamos = c.get("/api/prestamos", headers=h).json
            self.assertEqual([(p["id"], p["estado"]) for p in prestamos], [(1, "activo")])
            d = c.post("/api/prestamos/1/devolucion", headers=h)
            self.assertEqual(d.status_code, 200, d.json)

            # Segunda ejecución: las migraciones no se repiten ni duplican datos.
            c2 = create_app(f"sqlite:///{ruta}", datos_demo=True, secret_key="k").test_client()
            self.assertEqual(len(c2.get("/api/usuarios", headers=h).json), len(usuarios))

    def test_base_nueva_se_crea_con_alembic_y_conserva_datos_al_reiniciar(self):
        with TemporaryDirectory() as d:
            url = f"sqlite:///{Path(d) / 'nueva.sqlite'}"
            c1 = create_app(url, datos_demo=True, secret_key="k").test_client()
            h = {"Authorization": "Bearer " + c1.post("/api/auth/login", json={
                "correo": "admin@escuela.edu", "password": CLAVE}).json["token"]}
            c1.post("/api/prestamos", headers=h, json={"usuario_id": 2, "item_id": 1})
            c2 = create_app(url, datos_demo=True, secret_key="k").test_client()
            self.assertEqual(c2.get("/api/items/1").json["estado"], "PRESTADO")
            self.assertEqual(c2.get("/api/items").json["total"], 3)
            con = sqlite3.connect(Path(d) / "nueva.sqlite")
            self.assertEqual(con.execute("SELECT version_num FROM alembic_version").fetchone()[0], "0003")

    def test_claves_foraneas_activas(self):
        with TemporaryDirectory() as d:
            ruta = Path(d) / "fk.sqlite"
            create_app(f"sqlite:///{ruta}", datos_demo=True, secret_key="k")
            from prestamos_academicos.infraestructura.persistencia.conexion import crear_fabrica_sesiones
            motor, _ = crear_fabrica_sesiones(f"sqlite:///{ruta}")
            with motor.connect() as con:
                self.assertEqual(con.exec_driver_sql("PRAGMA foreign_keys").scalar(), 1)


class SinDatosDemoTest(unittest.TestCase):
    def test_sin_demo_solo_se_crea_el_gestor_indicado(self):
        import os
        os.environ["ADMIN_CORREO"], os.environ["ADMIN_PASSWORD"] = "root@escuela.edu", "clave-larga-1"
        try:
            c = create_app("sqlite+pysqlite:///:memory:", datos_demo=False, secret_key="k").test_client()
        finally:
            del os.environ["ADMIN_CORREO"], os.environ["ADMIN_PASSWORD"]
        self.assertEqual(c.get("/api/items").json["total"], 0)
        r = c.post("/api/auth/login", json={"correo": "root@escuela.edu", "password": "clave-larga-1"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(c.post("/api/auth/login", json={
            "correo": "admin@escuela.edu", "password": CLAVE}).status_code, 401)

    def test_instalacion_limpia_permite_crear_usuarios_y_recursos(self):
        with TemporaryDirectory() as d:
            url = f"sqlite:///{Path(d) / 'limpia.sqlite'}"
            with patch.dict(os.environ, {
                "ADMIN_CORREO": "gestor@escuela.edu",
                "ADMIN_PASSWORD": "clave-inicial-segura",
            }):
                os.environ.pop("DATOS_DEMO", None)
                cliente = create_app(url, secret_key="k").test_client()
            self.assertEqual(cliente.get("/api/items").json["total"], 0)
            acceso = cliente.post("/api/auth/login", json={
                "correo": "gestor@escuela.edu", "password": "clave-inicial-segura"})
            self.assertEqual(acceso.status_code, 200)
            cabeceras = {"Authorization": f"Bearer {acceso.json['token']}"}
            usuarios = cliente.get("/api/usuarios", headers=cabeceras).json
            self.assertEqual([u["correo"] for u in usuarios], ["gestor@escuela.edu"])

            nuevo_usuario = cliente.post("/api/usuarios", headers=cabeceras, json={
                "nombre": "Usuario de prueba", "correo": "prueba@escuela.edu",
                "perfiles": {"ESTUDIANTE": {"codigo_estudiante": "EST-PRUEBA"}},
            })
            self.assertEqual(nuevo_usuario.status_code, 201, nuevo_usuario.json)
            nuevo_item = cliente.post("/api/items", headers=cabeceras, json={
                "tipo": "LIBRO", "codigo": "LIB-PRUEBA", "nombre": "Libro de prueba",
                "categoria": "Pruebas", "atributos": {
                    "isbn": "978-0000000001", "autor": "Autor ficticio",
                    "editorial": "Editorial ficticia"},
            })
            self.assertEqual(nuevo_item.status_code, 201, nuevo_item.json)

            with patch.dict(os.environ, {"DATOS_DEMO": "0"}):
                os.environ.pop("ADMIN_CORREO", None)
                os.environ.pop("ADMIN_PASSWORD", None)
                reiniciado = create_app(url, secret_key="k").test_client()
            self.assertEqual(reiniciado.get("/api/items").json["total"], 1)
            self.assertEqual(reiniciado.get("/api/items").json["items"][0]["codigo"],
                             "LIB-PRUEBA")

    def test_base_vacia_sin_gestor_rechaza_arranque_sin_credenciales(self):
        with patch.dict(os.environ, {"DATOS_DEMO": "0"}):
            os.environ.pop("ADMIN_CORREO", None)
            os.environ.pop("ADMIN_PASSWORD", None)
            with self.assertRaisesRegex(RuntimeError, "ADMIN_CORREO y ADMIN_PASSWORD"):
                create_app("sqlite+pysqlite:///:memory:", secret_key="k")


if __name__ == "__main__":
    unittest.main()
