"""Conversión de objetos de dominio a JSON (contratos de la API)."""

from ..dominio.identidad import Permiso


def _fecha(valor):
    return valor.isoformat() if valor else None


def _pol(perfil):
    return perfil.politicaServicioId.valor if perfil and perfil.politicaServicioId else None


def usuario_a_json(usuario, permisos=None):
    perfiles = {}
    if usuario.perfilEstudiante:
        p = usuario.perfilEstudiante
        perfiles["ESTUDIANTE"] = {
            "codigo_estudiante": p.codigoEstudiante, "matricula_vigente": p.matriculaVigente,
            "politica_servicio_id": _pol(p)}
    if usuario.perfilDocente:
        p = usuario.perfilDocente
        perfiles["DOCENTE"] = {
            "codigo_empleado": p.codigoEmpleado, "tipo_contrato": p.tipoContrato,
            "vinculacion_vigente": p.vinculacionVigente,
            "politica_servicio_id": _pol(p)}
    if usuario.perfilAdministrativo:
        p = usuario.perfilAdministrativo
        perfiles["ADMINISTRATIVO"] = {
            "codigo_empleado": p.codigoEmpleado, "cargo_administrativo": p.cargoAdministrativo,
            "vinculacion_vigente": p.vinculacionVigente,
            "politica_servicio_id": _pol(p)}
    if usuario.perfilGestorInventario:
        p = usuario.perfilGestorInventario
        perfiles["GESTOR_INVENTARIO"] = {
            "codigo_empleado": p.codigoEmpleado, "area_responsable": p.areaResponsable,
            "fecha_asignacion": _fecha(p.fechaAsignacion)}
    if usuario.perfilAdministradorSistema:
        p = usuario.perfilAdministradorSistema
        perfiles["ADMINISTRADOR_SISTEMA"] = {
            "codigo_empleado": p.codigoEmpleado,
            "fecha_asignacion": _fecha(p.fechaAsignacion)}
    datos = {
        "id": usuario.id.valor,
        "nombre": usuario.nombre,
        "correo": usuario.correoElectronico,
        "activo": usuario.activo,
        "roles": [r.value for r in usuario.roles],
        "perfiles": perfiles,
        "tiene_sancion_activa": usuario.tieneSancionActiva(),
        "habilitado": usuario.estaHabilitado(),
        "motivo_no_habilitado": usuario.motivoNoHabilitado(),
    }
    if permisos is not None:
        datos["permisos"] = sorted(Permiso(p).value for p in permisos)
    return datos


def prestatario_a_json(usuario):
    return {"id": usuario.id.valor, "nombre": usuario.nombre}


def item_a_json(item):
    return {
        "id": item.id.valor,
        "codigo": item.codigo,
        "nombre": item.nombre,
        "categoria": item.categoria,
        "tipo": item.TIPO,
        "estado": item.estado.value,
        "disponible": item.estaDisponible(),
        "atributos": {k: v for k, v in item.atributosEspecificos().items() if v is not None},
    }


def tipo_a_json(tipo):
    return {
        "tipo": tipo.nombre,
        "etiqueta": tipo.etiqueta,
        "campos": [
            {"clave": c.clave, "etiqueta": c.etiqueta, "obligatorio": c.obligatorio}
            for c in tipo.campos
        ],
    }


def politica_a_json(p):
    return {
        "id": p.id.valor,
        "rol": p.rolAplicable.value,
        "max_items_simultaneos": p.maxItemsSimultaneos,
        "dias_prestamo_default": p.diasPrestamoDefault,
        "dias_gracia_reserva": p.diasGraciaReserva,
        "tipos_recurso_permitidos": [t for t in p.tiposRecursoPermitidos.split(",") if t],
    }
