"""Comprobación mínima de la factoría HTTP."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from prestamos_academicos.web import create_app
from prestamos_academicos.infraestructura.persistencia.base import Base
from prestamos_academicos.infraestructura.persistencia.modelos import UsuarioDB
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.cliente = create_app("sqlite+pysqlite:///:memory:").test_client()

    def test_salud(self):
        respuesta = self.cliente.get("/api/salud")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json, {"estado": "ok"})

    def test_prestar_y_devolver_actualiza_disponibilidad(self):
        recursos = self.cliente.get("/api/recursos").json
        usuarios = self.cliente.get("/api/usuarios").json
        self.assertEqual(
            [recurso["nombre"] for recurso in recursos],
            [
                "Introduction to Algorithms (CLRS)",
                "Clean Code: A Handbook of Agile Software Craftsmanship",
                "Meta Quest",
            ],
        )
        self.assertEqual(
            [usuario["nombre"] for usuario in usuarios],
            ["Jesus Perez", "Luis Ramos"],
        )

        datos = {"usuario_id": usuarios[0]["id"], "recurso_id": recursos[0]["id"]}
        prestamo = self.cliente.post("/api/prestamos", json=datos)
        self.assertEqual(prestamo.status_code, 201)
        self.assertEqual(prestamo.json["estado"], "activo")
        self.assertFalse(self.cliente.get("/api/recursos").json[0]["disponible"])
        self.assertEqual(len(self.cliente.get("/api/prestamos").json), 1)

        repetido = self.cliente.post("/api/prestamos", json=datos)
        self.assertEqual(repetido.status_code, 409)

        devolucion = self.cliente.post(
            f"/api/prestamos/{prestamo.json['id']}/devolucion"
        )
        self.assertEqual(devolucion.status_code, 200)
        self.assertEqual(devolucion.json["estado"], "devuelto")
        self.assertTrue(self.cliente.get("/api/recursos").json[0]["disponible"])

        segunda_devolucion = self.cliente.post(
            f"/api/prestamos/{prestamo.json['id']}/devolucion"
        )
        self.assertEqual(segunda_devolucion.status_code, 409)

        nuevo_prestamo = self.cliente.post("/api/prestamos", json=datos)
        self.assertEqual(nuevo_prestamo.status_code, 201)

    def test_rechaza_datos_invalidos(self):
        self.assertEqual(self.cliente.post("/api/prestamos", json={}).status_code, 400)
        self.assertEqual(
            self.cliente.post("/api/prestamos", json={"usuario_id": 999, "recurso_id": 1}).status_code,
            404,
        )

    def test_prestamo_persiste_tras_reiniciar_la_aplicacion(self):
        with TemporaryDirectory() as directorio:
            url = f"sqlite:///{Path(directorio) / 'mvp.sqlite'}"
            primer_cliente = create_app(url).test_client()
            prestamo = primer_cliente.post(
                "/api/prestamos", json={"usuario_id": 1, "recurso_id": 1}
            )
            self.assertEqual(prestamo.status_code, 201)

            segundo_cliente = create_app(url).test_client()
            self.assertEqual(len(segundo_cliente.get("/api/prestamos").json), 1)
            self.assertEqual(len(segundo_cliente.get("/api/usuarios").json), 2)
            self.assertEqual(len(segundo_cliente.get("/api/recursos").json), 3)
            self.assertFalse(segundo_cliente.get("/api/recursos").json[0]["disponible"])

    def test_actualiza_usuarios_del_demo_anterior(self):
        with TemporaryDirectory() as directorio:
            url = f"sqlite:///{Path(directorio) / 'demo_anterior.sqlite'}"
            motor = create_engine(url)
            Base.metadata.create_all(motor)
            with Session(motor) as sesion:
                sesion.add_all([
                    UsuarioDB(nombre="Ana Torres"),
                    UsuarioDB(nombre="Luis Rivera"),
                ])
                sesion.commit()

            cliente = create_app(url).test_client()
            self.assertEqual(
                [usuario["nombre"] for usuario in cliente.get("/api/usuarios").json],
                ["Jesus Perez", "Luis Ramos"],
            )
