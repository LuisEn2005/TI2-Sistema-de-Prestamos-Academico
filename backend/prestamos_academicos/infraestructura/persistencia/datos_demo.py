"""Carga inicial pequeña e idempotente para poder probar el MVP."""

from sqlalchemy import select, update

from .modelos import RecursoDB, UsuarioDB


def cargar_datos_demo(fabrica_sesiones):
    with fabrica_sesiones.begin() as sesion:
        if sesion.scalar(select(UsuarioDB.id).limit(1)) is None:
            sesion.add_all([
                UsuarioDB(nombre="Jesus Perez"),
                UsuarioDB(nombre="Luis Ramos"),
            ])
        else:
            # Actualiza únicamente los nombres de la primera versión del demo.
            sesion.execute(
                update(UsuarioDB)
                .where(UsuarioDB.nombre == "Ana Torres")
                .values(nombre="Jesus Perez")
            )
            sesion.execute(
                update(UsuarioDB)
                .where(UsuarioDB.nombre == "Luis Rivera")
                .values(nombre="Luis Ramos")
            )

        if sesion.scalar(select(RecursoDB.id).limit(1)) is None:
            sesion.add_all([
                RecursoDB(codigo="LIB-CLRS", nombre="Introduction to Algorithms (CLRS)", tipo="Libro"),
                RecursoDB(codigo="LIB-CLEAN", nombre="Clean Code: A Handbook of Agile Software Craftsmanship", tipo="Libro"),
                RecursoDB(codigo="EQ-META", nombre="Meta Quest", tipo="Equipo"),
            ])
