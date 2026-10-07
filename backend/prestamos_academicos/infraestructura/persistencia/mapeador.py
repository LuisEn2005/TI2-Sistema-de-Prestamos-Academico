"""DomainMapper: convierte entre objetos del dominio y modelos ORM."""

from __future__ import annotations

from ...dominio.configuracion import PoliticaServicio
from ...dominio.identidad import (
    PerfilAdministrativo, PerfilDocente, PerfilEstudiante, PerfilGestorInventario, Usuario,
)
from ...dominio.inventario import EstadoItem
from ...dominio.inventario.TiposItem import obtener_tipo
from ...dominio.prestamos import DetallePrestamo, EstadoPrestamo, Prestamo
from ...dominio.shared_kernel import (
    ItemId, PoliticaServicioId, PrestamoId, RolUsuario, UsuarioId,
)
from .modelos import (
    ItemDB, PerfilAdministrativoDB, PerfilDocenteDB, PerfilEstudianteDB,
    PerfilGestorInventarioDB, PoliticaServicioDB, PrestamoDB, UsuarioDB,
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
    usuario = Usuario(
        id=UsuarioId(fila.id),
        nombre=fila.nombre,
        correoElectronico=fila.correo,
        tieneSancionActivaCache=fila.tiene_sancion_activa_cache,
        activo=fila.activo,
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


# ---- Préstamos ----------------------------------------------------------
def prestamo_a_dominio(fila: PrestamoDB) -> Prestamo:
    return Prestamo(
        id=PrestamoId(fila.id),
        usuarioId=UsuarioId(fila.usuario_id),
        fechaEntrega=fila.fecha_prestamo,
        fechaDevolucionReal=fila.fecha_devolucion,
        estado=EstadoPrestamo.DEVUELTO if fila.fecha_devolucion else EstadoPrestamo.ACTIVO,
        detalles=[DetallePrestamo(itemId=ItemId(fila.item_id))],
    )
