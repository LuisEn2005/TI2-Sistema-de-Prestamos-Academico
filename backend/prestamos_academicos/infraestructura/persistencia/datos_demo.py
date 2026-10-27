"""Datos iniciales. Los usuarios y recursos de demostración son opcionales (DATOS_DEMO)."""

from sqlalchemy import update
from werkzeug.security import check_password_hash

from ...aplicacion.configuracion_service import ConfiguracionApplicationService
from ...aplicacion.identidad_service import IdentidadApplicationService
from ...aplicacion.inventario_service import InventarioApplicationService
from ...compartido import RolUsuario
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
    dict(tipo="LIBRO", codigo="LIB-DDIA",
         nombre="Designing Data-Intensive Applications",
         categoria="Sistemas distribuidos",
         atributos=dict(isbn="978-1449373320", autor="Martin Kleppmann",
                        editorial="O'Reilly Media")),
    dict(tipo="LIBRO", codigo="LIB-OS", nombre="Operating System Concepts",
         categoria="Sistemas operativos",
         atributos=dict(isbn="978-1119800361",
                        autor="Abraham Silberschatz, Peter B. Galvin, Greg Gagne",
                        editorial="Wiley")),
    dict(tipo="LIBRO", codigo="LIB-NET", nombre="Computer Networks",
         categoria="Redes",
         atributos=dict(isbn="978-0136764052",
                        autor="Andrew S. Tanenbaum, Nick Feamster, David Wetherall",
                        editorial="Pearson")),
    dict(tipo="LIBRO", codigo="LIB-DB", nombre="Database System Concepts",
         categoria="Bases de datos",
         atributos=dict(isbn="978-0078022159",
                        autor="Abraham Silberschatz, Henry F. Korth, S. Sudarshan",
                        editorial="McGraw-Hill")),
    dict(tipo="LIBRO", codigo="LIB-AIMA",
         nombre="Artificial Intelligence: A Modern Approach",
         categoria="Inteligencia artificial",
         atributos=dict(isbn="978-0134610993", autor="Stuart Russell, Peter Norvig",
                        editorial="Pearson")),
    dict(tipo="LIBRO", codigo="LIB-GOF", nombre="Design Patterns",
         categoria="Ingeniería de software",
         atributos=dict(isbn="978-0201633610",
                        autor="Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides",
                        editorial="Addison-Wesley")),
    dict(tipo="EQUIPO", codigo="EQ-LAP-002", nombre="Laptop Lenovo ThinkPad E14",
         categoria="Computación",
         atributos=dict(numeroSerie="LNV-E14-0002", marcaModelo="Lenovo ThinkPad E14")),
    dict(tipo="EQUIPO", codigo="EQ-RPI-001", nombre="Kit Raspberry Pi 5",
         categoria="Sistemas embebidos",
         atributos=dict(numeroSerie="RPI5-KIT-0001", marcaModelo="Raspberry Pi 5")),
    dict(tipo="EQUIPO", codigo="EQ-ARD-001", nombre="Kit Arduino UNO R4",
         categoria="Sistemas embebidos",
         atributos=dict(numeroSerie="ARD-R4-0001", marcaModelo="Arduino UNO R4")),
    dict(tipo="EQUIPO", codigo="EQ-ESP-001", nombre="Kit de desarrollo ESP32",
         categoria="Internet de las cosas",
         atributos=dict(numeroSerie="ESP32-0001", marcaModelo="ESP32 DevKit")),
    dict(tipo="EQUIPO", codigo="EQ-SW-001", nombre="Switch administrable",
         categoria="Redes",
         atributos=dict(numeroSerie="SW-CBS250-0001", marcaModelo="Cisco CBS250")),
    dict(tipo="EQUIPO", codigo="EQ-RTR-001", nombre="Router inalámbrico",
         categoria="Redes",
         atributos=dict(numeroSerie="RTR-AX55-0001", marcaModelo="TP-Link Archer AX55")),
    dict(tipo="EQUIPO", codigo="EQ-PRO-001", nombre="Proyector multimedia",
         categoria="Audiovisuales",
         atributos=dict(numeroSerie="PRO-EPS-0001", marcaModelo="Epson PowerLite")),
    dict(tipo="EQUIPO", codigo="EQ-CAM-001", nombre="Cámara web",
         categoria="Audiovisuales",
         atributos=dict(numeroSerie="CAM-C920-0001", marcaModelo="Logitech C920")),
    dict(tipo="MATERIAL", codigo="MAT-HDMI-001", nombre="Cable HDMI de 2 metros",
         categoria="Conectividad",
         atributos=dict(tipoMaterial="Cable HDMI", unidadMedida="unidad")),
    dict(tipo="MATERIAL", codigo="MAT-USBC-001", nombre="Adaptador multipuerto USB-C",
         categoria="Conectividad",
         atributos=dict(tipoMaterial="Adaptador", unidadMedida="unidad")),
    dict(tipo="MATERIAL", codigo="MAT-ETH-001", nombre="Cable de red Cat 6 de 5 metros",
         categoria="Redes",
         atributos=dict(tipoMaterial="Cable de red", unidadMedida="unidad")),
    dict(tipo="MATERIAL", codigo="MAT-JMP-001", nombre="Juego de cables jumper",
         categoria="Electrónica",
         atributos=dict(tipoMaterial="Cable jumper", unidadMedida="juego")),
    dict(tipo="MATERIAL", codigo="MAT-BRD-001", nombre="Protoboard",
         categoria="Electrónica",
         atributos=dict(tipoMaterial="Placa de pruebas", unidadMedida="unidad")),
    dict(tipo="MATERIAL", codigo="MAT-PWR-001", nombre="Regleta con protección eléctrica",
         categoria="Energía",
         atributos=dict(tipoMaterial="Regleta eléctrica", unidadMedida="unidad")),
    dict(tipo="MOBILIARIO", codigo="MOB-SILLA-001", nombre="Silla ergonómica",
         categoria="Laboratorio",
         atributos=dict(tipoMobiliario="Silla", ubicacionHabitual="Laboratorio de cómputo")),
    dict(tipo="MOBILIARIO", codigo="MOB-RACK-001", nombre="Rack para equipos de red",
         categoria="Redes",
         atributos=dict(tipoMobiliario="Rack", ubicacionHabitual="Laboratorio de redes")),
    dict(tipo="MOBILIARIO", codigo="MOB-PIZ-001", nombre="Pizarra acrílica móvil",
         categoria="Aulas",
         atributos=dict(tipoMobiliario="Pizarra", ubicacionHabitual="Aula de proyectos")),
]


def preparar_datos(fabrica_sesiones, *, datos_demo, admin_correo=None, admin_password=None):
    def uow():
        return SqlAlchemyUnitOfWork(fabrica_sesiones)

    configuracion = ConfiguracionApplicationService(uow)
    configuracion.asegurar_politicas_base()
    configuracion.asegurar_modalidades_base()
    identidad = IdentidadApplicationService(uow)

    if datos_demo:
        _actualizar_nombres_demo_anteriores(fabrica_sesiones)
        identidad.asegurar_administrador_inicial(admin_correo or CORREO_ADMIN_DEMO,
                                                 admin_password or PASSWORD_DEMO)
        _cargar_demo(uow, identidad)
    else:
        if bool(admin_correo) != bool(admin_password):
            raise RuntimeError("Configure ADMIN_CORREO y ADMIN_PASSWORD juntos.")
        with uow() as u:
            hay_admin = bool(u.usuarios.listar(rol=RolUsuario.ADMINISTRADOR_SISTEMA))
        if not hay_admin and not (admin_correo and admin_password):
            raise RuntimeError(
                "La base está vacía: configure ADMIN_CORREO y ADMIN_PASSWORD "
                "para crear el primer administrador, o active DATOS_DEMO=1 para pruebas.")
        if admin_correo and admin_password:
            identidad.asegurar_administrador_inicial(admin_correo, admin_password)


def _actualizar_nombres_demo_anteriores(fabrica_sesiones):
    with fabrica_sesiones.begin() as sesion:
        for viejo, nuevo in (("Ana Torres", "Jesus Perez"), ("Luis Rivera", "Luis Ramos")):
            sesion.execute(update(UsuarioDB).where(UsuarioDB.nombre == viejo).values(nombre=nuevo))


def _cargar_demo(uow, identidad):
    with uow() as u:
        administrador = next(iter(u.usuarios.listar(
            rol=RolUsuario.ADMINISTRADOR_SISTEMA)), None)
    _asegurar_usuario_demo(
        uow, identidad, administrador,
        nombre="Jesus Perez", correo="jesus.perez@escuela.edu",
        perfiles={"ESTUDIANTE": {
            "codigo_estudiante": "EST-2026-001", "matricula_vigente": True}},
    )
    _asegurar_usuario_demo(
        uow, identidad, administrador,
        nombre="Luis Ramos", correo="luis.ramos@escuela.edu",
        perfiles={
            # Los usuarios del MVP recibieron un perfil de estudiante provisional.
            # Luis es el gestor/docente de demostración, por lo que se reemplaza.
            "ESTUDIANTE": None,
            "DOCENTE": {"codigo_empleado": "DOC-001", "tipo_contrato": "Tiempo completo",
                         "vinculacion_vigente": True},
            "GESTOR_INVENTARIO": {"codigo_empleado": "DOC-001",
                                   "area_responsable": "Laboratorios"},
        },
    )

    inventario = InventarioApplicationService(uow)
    for item in _ITEMS_DEMO:
        with uow() as u:
            existe = u.items.find_by_codigo(item["codigo"]) is not None
        if not existe:
            inventario.registrar_item(item)


def _asegurar_usuario_demo(uow, identidad, administrador, *, nombre, correo, perfiles):
    """Crea o repara una cuenta demo sin perder su id ni su historial heredado."""
    with uow() as u:
        usuario = u.usuarios.find_by_email(correo)
        if usuario is None:
            usuario = next((x for x in u.usuarios.listar(texto=nombre)
                            if x.nombre == nombre
                            and x.correoElectronico.endswith("@sin-correo.local")), None)
        password_hash = (u.usuarios.password_hash_de(usuario.id.valor)
                         if usuario is not None else None)

    if usuario is None:
        identidad.registrar_usuario({
            "nombre": nombre, "correo": correo, "password": PASSWORD_DEMO,
            "perfiles": {rol: datos for rol, datos in perfiles.items() if datos is not None},
        })
        return

    datos = {"nombre": nombre, "correo": correo, "activo": True, "perfiles": perfiles}
    if not password_hash or not check_password_hash(password_hash, PASSWORD_DEMO):
        datos["password"] = PASSWORD_DEMO
    identidad.actualizar_usuario(usuario.id.valor, datos, administrador)
