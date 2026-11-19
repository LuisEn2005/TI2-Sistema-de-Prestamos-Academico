"""Datos iniciales. Los usuarios y recursos de demostración son opcionales (DATOS_DEMO)."""

from functools import cache

from sqlalchemy import update
from werkzeug.security import generate_password_hash

from ..configuracion_servicio.servicio import ConfiguracionApplicationService
from ..identidad.servicio import IdentidadApplicationService
from ..inventario.servicio import InventarioApplicationService
from ..compartido import RolUsuario
from .modelos import UsuarioDB
from .unidad_trabajo import SqlAlchemyUnitOfWork

PASSWORD_DEMO = "demo1234"
CORREO_ADMIN_DEMO = "admin@escuela.edu"

# Padrón del curso: (nombre, usuario del correo, código de estudiante).
_ESTUDIANTES_DEMO = [
    ("Jesus Alberto Alfaro Buiza", "jesus.alfaro", "20230114"),
    ("Marco Antonio Armendariz Paredes", "marco.armendariz", "20230127"),
    ("Albert Gussepe Blanco Cana", "albert.blanco", "20220389"),
    ("Karina Paola Calcina Chuquipalla", "karina.calcina", "20240152"),
    ("Diego Canqui Ecos", "diego.canqui", "20230166"),
    ("Anderson Samuel Carpio Chura", "anderson.carpio", "20240173"),
    ("Moises Robert Ccaso Idme", "moises.ccaso", "20230198"),
    ("Elyud Edgar Chayña Calcina", "elyud.chayna", "20210455"),
    ("Luis Antonio Chipana Chura", "luis.chipana", "20230211"),
    ("Aldair Daniel Condori Ataucuri", "aldair.condori", "20240236"),
    ("Emilio Alejandro Condori Pallardel", "emilio.condori", "20230249"),
    ("Stephano Gian Pierre Delgado Chavez", "stephano.delgado", "20230262"),
    ("Mauricio Alejandro Farfan Huayta", "mauricio.farfan", "20240278"),
    ("Fernando Antonio Gama Llicahua", "fernando.gama", "20230291"),
    ("Carlos Enrique Gutierrez Castilla", "carlos.gutierrez", "20220417"),
    ("Johan Diego Huamani Sabina", "johan.huamani", "20240305"),
    ("Estrella de Jesús Emilia Fabiana Huarsaya Márquez", "estrella.huarsaya", "20230318"),
    ("Lizzy Arlette Huayhua Perez", "lizzy.huayhua", "20230324"),
    ("Roid Niro Huaylla Guzman", "roid.huaylla", "20230337"),
    ("Daysi Jara Arisaca", "daysi.jara", "20240349"),
    ("Hellen Grace Juan de Dios Delgado", "hellen.juandedios", "20230356"),
    ("Natalie Marleny Lazo Paxi", "natalie.lazo", "20230363"),
    ("Fernando Enrique Llosa Manchego", "fernando.llosa", "20220442"),
    ("Mariana Valery Luis Jimenez", "mariana.luis", "20240381"),
    ("Diego de Alessandro Mamani Salazar", "diego.mamani", "20230394"),
    ("Luis Fernando Morales Tacca", "luis.morales", "20230402"),
    ("Neill Elverth Olazabal Chavez", "neill.olazabal", "20240415"),
    ("Alvaro Johan Panibra Choctaya", "alvaro.panibra", "20230428"),
    ("Javier Alonzo Peñalva Humire", "javier.penalva", "20230436"),
    ("Jesus Gustavo Perez Villasante", "jesus.perez", "20230447"),
    ("Juan Carlos Postigo Cabana", "juan.postigo", "20220463"),
    ("Claudia Roxana Quisocala Cruz", "claudia.quisocala", "20230459"),
    ("Sharmely Yesenia Quispe Chavez", "sharmely.quispe", "20240467"),
    ("David Augusto Quispe Lloccallasi", "david.quispe", "20230471"),
    ("Angelo Josue Quispe Suarez", "angelo.quispe", "20230484"),
    ("Job Lorenzo Quispe Torrez", "lorenzo.quispe", "20240841"),
    ("Luis Enrique Ramos Chambi", "luis.ramos", "20230497"),
    ("Rodrigo Abraham Ramos Mamani", "rodrigo.ramos", "20230503"),
    ("Omar Joaquin Rivera Olivera", "omar.rivera", "20240516"),
    ("Edu Andre Sucari Ccansaya", "edu.sucari", "20230529"),
    ("Cristhian Luis Taipe Huanca", "cristhian.taipe", "20220534"),
    ("Lizeth Angelica Tito Vilca", "lizeth.tito", "20230542"),
    ("Jhair Alejandro Torres Chavez", "jhair.torres", "20230555"),
    ("Micaela Belen Uribe Zuñiga", "micaela.uribe", "20230568"),
    ("Ronald Reynaldo Valdez Agüero", "ronald.valdez", "20230571"),
    ("Diego Mauricio Villanueva Flores", "diego.villanueva", "20240584"),
    ("Marving Alonzo Zamata Huaracha", "marving.zamata", "20230597"),
    ("Eduardo Josue Zela Quispe", "eduardo.zela", "20230603"),
]
# Estudiantes que además atienden el inventario (practicantes de laboratorio).
_GESTORES_DEMO = {"luis.ramos": "GES-001", "lorenzo.quispe": "GES-002"}


def _padron_demo():
    """(nombre, correo, perfiles) de cada persona de demostración."""
    for nombre, usuario, codigo in _ESTUDIANTES_DEMO:
        perfiles = {"ESTUDIANTE": {"codigo_estudiante": codigo, "matricula_vigente": True},
                    "DOCENTE": None}
        if usuario in _GESTORES_DEMO:
            perfiles["GESTOR_INVENTARIO"] = {"codigo_empleado": _GESTORES_DEMO[usuario],
                                             "area_responsable": "Laboratorios"}
        yield nombre, f"{usuario}@escuela.edu", perfiles
    yield "Yessenia Deysi Yari Ramos", "yessenia.yari@escuela.edu", {
        "DOCENTE": {"codigo_empleado": "DOC-001", "tipo_contrato": "Tiempo completo",
                     "vinculacion_vigente": True}}


@cache
def _hash_demo():
    # Un solo hash para todo el padrón: scrypt tarda ~70 ms por cálculo.
    return generate_password_hash(PASSWORD_DEMO)


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
    configuracion.asegurar_modalidades_base()
    configuracion.asegurar_politicas_base()
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
        for viejo, nuevo in (("Ana Torres", "Jesus Gustavo Perez Villasante"),
                             ("Luis Rivera", "Luis Enrique Ramos Chambi")):
            sesion.execute(update(UsuarioDB).where(UsuarioDB.nombre == viejo).values(nombre=nuevo))


def _cargar_demo(uow, identidad):
    with uow() as u:
        administrador = next(iter(u.usuarios.listar(
            rol=RolUsuario.ADMINISTRADOR_SISTEMA)), None)
    padron = list(_padron_demo())
    for nombre, correo, perfiles in padron:
        _asegurar_usuario_demo(uow, identidad, administrador,
                               nombre=nombre, correo=correo, perfiles=perfiles)
    with uow() as u:
        u.sesion.execute(update(UsuarioDB)
                         .where(UsuarioDB.password_hash.is_(None),
                                UsuarioDB.correo.in_([c for _, c, _ in padron]))
                         .values(password_hash=_hash_demo()))
        u.commit()

    inventario = InventarioApplicationService(uow)
    for item in _ITEMS_DEMO:
        with uow() as u:
            existe = u.items.find_by_codigo(item["codigo"]) is not None
        if not existe:
            inventario.registrar_item(item)


def _asegurar_usuario_demo(uow, identidad, administrador, *, nombre, correo, perfiles):
    """Crea o repara una cuenta demo sin perder su id ni su historial heredado.

    La contraseña la asigna después `_cargar_demo` en bloque a las cuentas sin una."""
    with uow() as u:
        usuario = u.usuarios.find_by_email(correo)
        if usuario is None:
            usuario = next((x for x in u.usuarios.listar(texto=nombre)
                            if x.nombre == nombre
                            and x.correoElectronico.endswith("@sin-correo.local")), None)

    if usuario is None:
        identidad.registrar_usuario({
            "nombre": nombre, "correo": correo,
            "perfiles": {rol: datos for rol, datos in perfiles.items() if datos is not None},
        })
        return
    identidad.actualizar_usuario(
        usuario.id.valor,
        {"nombre": nombre, "correo": correo, "activo": True, "perfiles": perfiles},
        administrador)
