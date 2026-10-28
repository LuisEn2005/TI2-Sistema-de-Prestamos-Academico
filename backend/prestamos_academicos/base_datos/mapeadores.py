"""DomainMapper: convierte entre objetos del dominio y modelos ORM."""

from __future__ import annotations

from ..configuracion_servicio import Modalidad, PoliticaServicio
from ..identidad import (
    PerfilAdministradorSistema, PerfilAdministrativo, PerfilDocente, PerfilEstudiante,
    PerfilGestorInventario, Usuario,
)
from ..inventario import EstadoItem
from ..inventario import obtener_tipo
from ..prestamos import (
    CondicionDevolucion, DetallePrestamo, EstadoPrestamo, ModalidadSnapshot, Prestamo,
)
from ..reservas import EstadoReserva, Reserva
from ..compartido import (
    ItemId, ModalidadId, PoliticaServicioId, PrestamoId, ReservaId, RolUsuario, UsuarioId,
)
from .modelos import (
    DetallePrestamoDB, ItemDB, ModalidadDB, PerfilAdministrativoDB, PerfilDocenteDB, PerfilEstudianteDB,
    PerfilAdministradorSistemaDB, PerfilGestorInventarioDB, PoliticaServicioDB,
    PrestamoDB, ReservaDB, UsuarioDB,
)


def _pid(valor):
    return None if valor is None else PoliticaServicioId(valor)


def _raw(identificador):
    return None if identificador is None else identificador.valor


# ---- Políticas ----------------------------------------------------------
def politica_a_dominio(fila: PoliticaServicioDB) -> PoliticaServicio:
    return PoliticaServicio(
        id=PoliticaServicioId(fila.id),
        rolAplicable=RolUsuario(fila.rol_aplicable),
        maxItemsSimultaneos=fila.max_items_simultaneos,
        diasPrestamoDefault=fila.dias_prestamo_default,
        diasGraciaReserva=fila.dias_gracia_reserva,
        tiposRecursoPermitidos=fila.tipos_recurso_permitidos,
    )


# ---- Usuarios -----------------------------------------------------------
def usuario_a_dominio(fila: UsuarioDB, perfiles: dict) -> Usuario:
    e = perfiles.get("estudiante")
    d = perfiles.get("docente")
    a = perfiles.get("administrativo")
    g = perfiles.get("gestor")
    adm = perfiles.get("administrador_sistema")
    usuario = Usuario(
        id=UsuarioId(fila.id),
        nombre=fila.nombre,
        correoElectronico=fila.correo,
        tieneSancionActivaCache=fila.tiene_sancion_activa_cache,
        activo=fila.activo,
        versionSesion=fila.version_sesion,
        perfilEstudiante=e and PerfilEstudiante(
            codigoEstudiante=e.codigo_estudiante, matriculaVigente=e.matricula_vigente,
            politicaServicioId=_pid(e.politica_servicio_id)),
        perfilDocente=d and PerfilDocente(
            codigoEmpleado=d.codigo_empleado, tipoContrato=d.tipo_contrato,
            vinculacionVigente=d.vinculacion_vigente,
            politicaServicioId=_pid(d.politica_servicio_id)),
        perfilAdministrativo=a and PerfilAdministrativo(
            codigoEmpleado=a.codigo_empleado, cargoAdministrativo=a.cargo_administrativo,
            vinculacionVigente=a.vinculacion_vigente,
            politicaServicioId=_pid(a.politica_servicio_id)),
        perfilGestorInventario=g and PerfilGestorInventario(
            g.codigo_empleado, g.area_responsable, g.fecha_asignacion),
        perfilAdministradorSistema=adm and PerfilAdministradorSistema(
            adm.codigo_empleado, adm.fecha_asignacion),
    )
    usuario.sincronizarRoles()
    return usuario


# ---- Ítems --------------------------------------------------------------
def item_a_dominio(fila: ItemDB):
    tipo = obtener_tipo(fila.tipo)
    atributos = {c.clave: (fila.atributos or {}).get(c.clave) for c in tipo.campos}
    return tipo.clase(
        id=ItemId(fila.id),
        codigo=fila.codigo,
        nombre=fila.nombre,
        categoria=fila.categoria,
        estado=EstadoItem(fila.estado),
        **atributos,
    )


def construir_texto_busqueda(item) -> str:
    partes = [item.codigo, item.nombre, item.categoria, item.TIPO]
    partes += [str(v) for v in item.atributosEspecificos().values() if v]
    return " ".join(p for p in partes if p).lower()


def item_a_orm(item, fila: ItemDB | None = None) -> ItemDB:
    fila = fila or ItemDB()
    fila.codigo = item.codigo
    fila.nombre = item.nombre
    fila.categoria = item.categoria
    fila.tipo = item.TIPO
    fila.estado = item.estado.value
    fila.atributos = {k: v for k, v in item.atributosEspecificos().items() if v is not None}
    fila.texto_busqueda = construir_texto_busqueda(item)
    return fila


# ---- Modalidades --------------------------------------------------------
def modalidad_a_dominio(fila: ModalidadDB) -> Modalidad:
    return Modalidad(id=ModalidadId(fila.id), nombre=fila.nombre,
                     diasPlazoDefault=fila.dias_plazo_default, activo=fila.activo)


# ---- Reservas -----------------------------------------------------------
def reserva_a_dominio(fila: ReservaDB) -> Reserva:
    return Reserva(
        id=ReservaId(fila.id),
        usuarioId=UsuarioId(fila.usuario_id),
        itemId=ItemId(fila.item_id),
        rolSolicitante=RolUsuario(fila.rol_solicitante),
        fechaSolicitud=fila.fecha_solicitud,
        fechaReserva=fila.fecha_reserva,
        fechaExpiracion=fila.fecha_expiracion,
        estado=EstadoReserva(fila.estado),
    )


# ---- Préstamos ----------------------------------------------------------
def prestamo_a_dominio(fila: PrestamoDB, detalles: list[DetallePrestamoDB]) -> Prestamo:
    modalidad = None
    if fila.modalidad_dias_plazo is not None:
        modalidad = ModalidadSnapshot(
            modalidadOrigenId=None if fila.modalidad_id is None else ModalidadId(fila.modalidad_id),
            nombre=fila.modalidad_nombre, diasPlazo=fila.modalidad_dias_plazo)
    return Prestamo(
        id=PrestamoId(fila.id),
        usuarioId=UsuarioId(fila.usuario_id),
        reservaId=ReservaId(fila.reserva_id) if fila.reserva_id else None,
        rolSolicitante=RolUsuario(fila.rol_solicitante) if fila.rol_solicitante else None,
        modalidad=modalidad,
        diasPlazoAplicado=fila.dias_plazo_aplicado,
        numeroRenovaciones=fila.numero_renovaciones,
        fechaEntrega=fila.fecha_prestamo,
        fechaDevolucionEsperada=fila.fecha_devolucion_esperada,
        fechaDevolucionReal=fila.fecha_devolucion,
        estado=EstadoPrestamo.DEVUELTO if fila.fecha_devolucion else EstadoPrestamo.ACTIVO,
        detalles=[
            DetallePrestamo(
                id=d.id, itemId=ItemId(d.item_id), observacion=d.observacion,
                condicion=CondicionDevolucion(d.condicion) if d.condicion else None)
            for d in sorted(detalles, key=lambda d: d.id)
        ],
    )
