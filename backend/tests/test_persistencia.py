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

            prestamos = c.get("/api/prestamos", headers=h).json["prestamos"]
            self.assertEqual([(p["id"], p["estado"]) for p in prestamos], [(1, "activo")])
            heredado_p = c.get("/api/prestamos/1", headers=h).json
            self.assertEqual([i["codigo"] for i in heredado_p["items"]], ["LIB-CLRS"])
            self.assertIsNone(heredado_p["modalidad"])          # el MVP no registraba modalidad
            self.assertIsNone(heredado_p["fecha_limite"])
            self.assertFalse(heredado_p["vencido"])
            d = c.post("/api/prestamos/1/devolucion", headers=h, json={"condiciones": [
                {"item_id": heredado_p["items"][0]["item_id"], "condicion": "BUEN_ESTADO"}]})
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
            modalidad = c1.get("/api/modalidades", headers=h).json[1]["id"]
            entrega = c1.post("/api/prestamos", headers=h, json={
                "usuario_id": 2, "item_ids": [1], "modalidad_id": modalidad})
            self.assertEqual(entrega.status_code, 201, entrega.json)
            c2 = create_app(url, datos_demo=True, secret_key="k").test_client()
            self.assertEqual(c2.get("/api/items/1").json["estado"], "PRESTADO")
            reabierto = c2.get("/api/prestamos", headers=h).json["prestamos"]
            self.assertEqual([(p["modalidad"], len(p["items"])) for p in reabierto],
                             [("Externa (a domicilio)", 1)])
            self.assertEqual(c2.get("/api/items").json["total"], 3)
            con = sqlite3.connect(Path(d) / "nueva.sqlite")
            self.assertEqual(con.execute("SELECT version_num FROM alembic_version").fetchone()[0], "0007")

    def test_claves_foraneas_activas(self):
        with TemporaryDirectory() as d:
            ruta = Path(d) / "fk.sqlite"
            create_app(f"sqlite:///{ruta}", datos_demo=True, secret_key="k")
            from prestamos_academicos.infraestructura.persistencia.conexion import crear_fabrica_sesiones
            motor, _ = crear_fabrica_sesiones(f"sqlite:///{ruta}")
            with motor.connect() as con:
                self.assertEqual(con.exec_driver_sql("PRAGMA foreign_keys").scalar(), 1)

    def test_restricciones_rechazan_estado_y_codigo_no_canonicos(self):
        from sqlalchemy import text
        from sqlalchemy.exc import IntegrityError
        from prestamos_academicos.infraestructura.persistencia.conexion import crear_fabrica_sesiones

        with TemporaryDirectory() as d:
            ruta = Path(d) / "integridad.sqlite"
            create_app(f"sqlite:///{ruta}", datos_demo=True, secret_key="k")
            motor, _ = crear_fabrica_sesiones(f"sqlite:///{ruta}")
            with self.assertRaises(IntegrityError), motor.begin() as con:
                con.execute(text("UPDATE items SET estado = 'ROTO' WHERE codigo = 'LIB-CLRS'"))
            with self.assertRaises(IntegrityError), motor.begin() as con:
                con.execute(text("UPDATE items SET codigo = 'lib-clrs' WHERE codigo = 'LIB-CLRS'"))


class MigracionDelSprint2Test(unittest.TestCase):
    """Una base del Sprint 2 con préstamos reales pasa al esquema de préstamos completos."""

    def _base_del_sprint_2(self, ruta):
        from alembic import command
        from sqlalchemy import create_engine, text
        from prestamos_academicos.infraestructura.persistencia.migraciones import (
            configuracion_alembic,
        )
        motor = create_engine(f"sqlite:///{ruta}")
        cfg = configuracion_alembic()
        with motor.connect() as con:
            con.exec_driver_sql("PRAGMA foreign_keys=OFF")
            con.commit()
            cfg.attributes["connection"] = con
            command.upgrade(cfg, "0006")
            con.commit()
        with motor.begin() as con:
            con.execute(text("INSERT INTO usuarios (nombre, correo, activo, version_sesion, "
                             "tiene_sancion_activa_cache, creado_en) VALUES "
                             "('Ana','ana@escuela.edu',1,0,0,'2026-01-01'),"
                             "('Beto','beto@escuela.edu',1,0,0,'2026-01-01')"))
            con.execute(text("INSERT INTO items (codigo,nombre,categoria,tipo,estado,atributos,"
                             "texto_busqueda,creado_en,actualizado_en) VALUES "
                             "('L1','Uno','C','LIBRO','PRESTADO','{}','l1','2026-01-01','2026-01-01'),"
                             "('L2','Dos','C','LIBRO','DISPONIBLE','{}','l2','2026-01-01','2026-01-01')"))
            con.execute(text("INSERT INTO prestamos (usuario_id,item_id,fecha_prestamo,fecha_devolucion)"
                             " VALUES (1,1,'2026-09-01 10:00:00',NULL),"
                             "(2,2,'2026-08-01 10:00:00','2026-08-03 10:00:00')"))
        motor.dispose()

    def test_los_prestamos_existentes_pasan_a_tener_un_detalle(self):
        from sqlalchemy import text
        from prestamos_academicos.infraestructura.persistencia.conexion import crear_fabrica_sesiones
        with TemporaryDirectory() as d:
            ruta = Path(d) / "sprint2.sqlite"
            self._base_del_sprint_2(ruta)
            c = create_app(f"sqlite:///{ruta}", datos_demo=True, secret_key="k").test_client()
            h = {"Authorization": "Bearer " + c.post("/api/auth/login", json={
                "correo": "admin@escuela.edu", "password": CLAVE}).json["token"]}
            lista = c.get("/api/prestamos", headers=h).json["prestamos"]
            por_usuario = {p["usuario"]: p for p in lista}
            self.assertEqual(por_usuario["Ana"]["estado"], "activo")
            self.assertEqual([i["codigo"] for i in por_usuario["Ana"]["items"]], ["L1"])
            self.assertEqual(por_usuario["Beto"]["estado"], "devuelto")
            self.assertIsNone(por_usuario["Beto"]["items"][0]["condicion"])   # no se registraba
            self.assertIsNone(por_usuario["Ana"]["fecha_limite"])
            self.assertEqual(c.get("/api/prestamos?estado=vencido", headers=h).json["total"], 0)
            # la devolución del préstamo heredado exige la condición y libera el ítem
            r = c.post(f"/api/prestamos/{por_usuario['Ana']['id']}/devolucion", headers=h, json={
                "condiciones": [{"item_id": por_usuario["Ana"]["items"][0]["item_id"],
                                 "condicion": "BUEN_ESTADO"}]})
            self.assertEqual(r.status_code, 200, r.json)
            self.assertEqual(c.get("/api/items?q=l1").json["items"][0]["estado"], "DISPONIBLE")
            motor, _ = crear_fabrica_sesiones(f"sqlite:///{ruta}")
            with motor.connect() as con:
                self.assertEqual(con.execute(text("SELECT count(*) FROM detalles_prestamo "
                                                  "WHERE activo")).scalar(), 0)
                self.assertEqual(con.exec_driver_sql("PRAGMA foreign_key_check").all(), [])

    def test_la_base_impide_dos_prestamos_activos_del_mismo_item(self):
        from sqlalchemy import text
        from sqlalchemy.exc import IntegrityError
        from prestamos_academicos.infraestructura.persistencia.conexion import crear_fabrica_sesiones
        with TemporaryDirectory() as d:
            ruta = Path(d) / "exclusividad.sqlite"
            create_app(f"sqlite:///{ruta}", datos_demo=True, secret_key="k")
            motor, _ = crear_fabrica_sesiones(f"sqlite:///{ruta}")
            with motor.begin() as con:
                con.execute(text("INSERT INTO prestamos (usuario_id, fecha_prestamo) "
                                 "VALUES (2, '2026-10-19 10:00:00'), (2, '2026-10-19 11:00:00')"))
                con.execute(text("INSERT INTO detalles_prestamo (prestamo_id,item_id,activo) "
                                 "VALUES (1,1,1)"))
            with self.assertRaises(IntegrityError), motor.begin() as con:
                con.execute(text("INSERT INTO detalles_prestamo (prestamo_id,item_id,activo) "
                                 "VALUES (2,1,1)"))
            with motor.begin() as con:     # tras devolverse, el ítem puede volver a prestarse
                con.execute(text("UPDATE detalles_prestamo SET activo = 0 WHERE prestamo_id = 1"))
                con.execute(text("INSERT INTO detalles_prestamo (prestamo_id,item_id,activo) "
                                 "VALUES (2,1,1)"))

    def test_las_modalidades_base_se_crean_una_sola_vez(self):
        with TemporaryDirectory() as d:
            url = f"sqlite:///{Path(d) / 'mod.sqlite'}"
            for _ in range(2):
                c = create_app(url, datos_demo=True, secret_key="k").test_client()
            h = {"Authorization": "Bearer " + c.post("/api/auth/login", json={
                "correo": "admin@escuela.edu", "password": CLAVE}).json["token"]}
            self.assertEqual(len(c.get("/api/modalidades", headers=h).json), 2)


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
        self.assertEqual(r.json["usuario"]["roles"], ["ADMINISTRADOR_SISTEMA"])
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
            self.assertEqual(usuarios[0]["roles"], ["ADMINISTRADOR_SISTEMA"])

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
