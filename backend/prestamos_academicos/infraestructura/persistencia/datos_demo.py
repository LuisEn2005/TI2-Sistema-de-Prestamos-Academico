"""Datos iniciales. Los usuarios y recursos de demostración son opcionales (DATOS_DEMO)."""

from sqlalchemy import select, update

from ...aplicacion.configuracion_service import ConfiguracionApplicationService
from ...aplicacion.identidad_service import IdentidadApplicationService
from ...aplicacion.inventario_service import InventarioApplicationService
from .modelos import UsuarioDB
from .unidad_trabajo import SqlAlchemyUnitOfWork

PASSWORD_DEMO = "demo1234"
CORREO_ADMIN_DEMO = "admin@escuela.edu"

_ITEMS_DEMO = [
    dict(tipo="LIBRO", codigo="LIB-CLRS", nombre="Introduction to Algorithms (CLRS)",
         categoria="Algoritmos",
         atributos=dict(isbn="978-0262046305", autor="Cormen, Leiserson, Rivest, Stein",
                        editorial="MIT Press")),
    dict(tipo="LIBRO", codigo="LIB-CLEAN",
         nombre="Clean Code: A Handbook of Agile Software Craftsmanship",
         categoria="Ingeniería de software",
         atributos=dict(isbn="978-0132350884", autor="Robert C. Martin",
                        editorial="Prentice Hall")),
    dict(tipo="EQUIPO", codigo="EQ-META", nombre="Meta Quest", categoria="Realidad virtual",
         atributos=dict(numeroSerie="MQ-0001", marcaModelo="Meta Quest 3")),
    dict(tipo="EQUIPO", codigo="EQ-LAP01", nombre="Laptop de laboratorio 01",
         categoria="Cómputo", atributos=dict(numeroSerie="LP-1001", marcaModelo="Lenovo ThinkPad")),
    dict(tipo="MATERIAL", codigo="MAT-ARD01", nombre="Kit Arduino Uno", categoria="Electrónica",
         atributos=dict(tipoMaterial="Kit de prototipado", unidadMedida="kit")),
    dict(tipo="MOBILIARIO", codigo="MOB-PIZ01", nombre="Pizarra móvil", categoria="Aulas",
         atributos=dict(tipoMobiliario="Pizarra", ubicacionHabitual="Laboratorio 2")),
]


def preparar_datos(fabrica_sesiones, *, datos_demo, admin_correo=None, admin_password=None):
    def uow():
        return SqlAlchemyUnitOfWork(fabrica_sesiones)

    ConfiguracionApplicationService(uow).asegurar_politicas_base()
    identidad = IdentidadApplicationService(uow)

    if datos_demo:
        _actualizar_nombres_demo_anteriores(fabrica_sesiones)
        identidad.asegurar_gestor_inicial(admin_correo or CORREO_ADMIN_DEMO,
                                          admin_password or PASSWORD_DEMO)
        _cargar_demo(uow, identidad)
    elif admin_correo and admin_password:
        identidad.asegurar_gestor_inicial(admin_correo, admin_password)


def _actualizar_nombres_demo_anteriores(fabrica_sesiones):
    with fabrica_sesiones.begin() as sesion:
        for viejo, nuevo in (("Ana Torres", "Jesus Perez"), ("Luis Rivera", "Luis Ramos")):
            sesion.execute(update(UsuarioDB).where(UsuarioDB.nombre == viejo).values(nombre=nuevo))


def _cargar_demo(uow, identidad):
    with uow() as u:
        hay_prestatarios = any(x.esPrestatario() for x in u.usuarios.listar())
        hay_items = bool(u.items.buscar(limite=1)[1])
    if not hay_prestatarios:
        identidad.registrar_usuario({
            "nombre": "Jesus Perez", "correo": "jesus.perez@escuela.edu",
            "password": PASSWORD_DEMO,
            "perfiles": {"ESTUDIANTE": {"codigo_estudiante": "EST-2026-001"}}})
        identidad.registrar_usuario({
            "nombre": "Luis Ramos", "correo": "luis.ramos@escuela.edu",
            "password": PASSWORD_DEMO,
            "perfiles": {
                "DOCENTE": {"codigo_empleado": "DOC-001", "tipo_contrato": "Tiempo completo"},
                "GESTOR_INVENTARIO": {"codigo_empleado": "DOC-001",
                                      "area_responsable": "Laboratorios"}}})
    if not hay_items:
        inventario = InventarioApplicationService(uow)
        for item in _ITEMS_DEMO:
            inventario.registrar_item(item)
