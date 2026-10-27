"""Normaliza datos y agrega restricciones de integridad.

Revision ID: 0004
Revises: 0003
"""

from alembic import op
import sqlalchemy as sa


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


ESTADOS = "'DISPONIBLE','PRESTADO','RESERVADO','EN_MANTENIMIENTO','DADO_DE_BAJA','EXTRAVIADO'"


def _restricciones(tabla, restricciones):
    with op.batch_alter_table(tabla) as lote:
        for nombre, expresion in restricciones:
            lote.create_check_constraint(nombre, expresion)


def upgrade():
    # Canoniza antes de imponer las reglas. Si existen duplicados que solo se
    # distinguen por mayúsculas o espacios, la restricción UNIQUE aborta la
    # migración y exige resolver la ambigüedad de forma explícita.
    op.execute("UPDATE usuarios SET nombre = trim(nombre), correo = lower(trim(correo))")
    op.execute("UPDATE perfiles_estudiante SET codigo_estudiante = trim(codigo_estudiante)")
    op.execute("UPDATE perfiles_docente SET codigo_empleado = trim(codigo_empleado), "
               "tipo_contrato = trim(tipo_contrato)")
    op.execute("UPDATE perfiles_administrativo SET codigo_empleado = trim(codigo_empleado), "
               "cargo_administrativo = trim(cargo_administrativo)")
    op.execute("UPDATE perfiles_gestor_inventario SET codigo_empleado = trim(codigo_empleado), "
               "area_responsable = trim(area_responsable)")
    op.execute("UPDATE items SET codigo = upper(trim(codigo)), nombre = trim(nombre), "
               "categoria = trim(categoria), tipo = upper(trim(tipo)), estado = upper(trim(estado))")
    op.execute("UPDATE items SET texto_busqueda = lower(codigo || ' ' || nombre || ' ' || "
               "categoria || ' ' || tipo || ' ' || CAST(atributos AS TEXT))")

    _restricciones("politicas_servicio", (
        ("ck_politica_max_positivo", "max_items_simultaneos > 0"),
        ("ck_politica_dias_positivo", "dias_prestamo_default > 0"),
        ("ck_politica_gracia_no_negativa", "dias_gracia_reserva >= 0"),
        ("ck_politica_tipos_no_vacios", "length(trim(tipos_recurso_permitidos)) > 0"),
    ))
    _restricciones("usuarios", (
        ("ck_usuario_nombre_no_vacio", "length(trim(nombre)) > 0"),
        ("ck_usuario_correo_canonico", "correo = lower(trim(correo))"),
        ("ck_usuario_correo_no_vacio", "length(trim(correo)) > 0"),
    ))
    _restricciones("perfiles_estudiante", (
        ("ck_estudiante_codigo_no_vacio", "length(trim(codigo_estudiante)) > 0"),
    ))
    _restricciones("perfiles_docente", (
        ("ck_docente_codigo_no_vacio", "length(trim(codigo_empleado)) > 0"),
        ("ck_docente_contrato_no_vacio", "length(trim(tipo_contrato)) > 0"),
    ))
    _restricciones("perfiles_administrativo", (
        ("ck_administrativo_codigo_no_vacio", "length(trim(codigo_empleado)) > 0"),
        ("ck_administrativo_cargo_no_vacio", "length(trim(cargo_administrativo)) > 0"),
    ))
    _restricciones("perfiles_gestor_inventario", (
        ("ck_gestor_codigo_no_vacio", "length(trim(codigo_empleado)) > 0"),
        ("ck_gestor_area_no_vacia", "length(trim(area_responsable)) > 0"),
    ))
    _restricciones("items", (
        ("ck_item_codigo_canonico", "codigo = upper(trim(codigo))"),
        ("ck_item_codigo_no_vacio", "length(trim(codigo)) > 0"),
        ("ck_item_nombre_no_vacio", "length(trim(nombre)) > 0"),
        ("ck_item_categoria_no_vacia", "length(trim(categoria)) > 0"),
        ("ck_item_tipo_no_vacio", "length(trim(tipo)) > 0"),
        ("ck_item_estado_valido", f"estado IN ({ESTADOS})"),
    ))
    _restricciones("prestamos", ((
        "ck_prestamo_fechas_ordenadas",
        "fecha_devolucion IS NULL OR fecha_devolucion >= fecha_prestamo",
    ),))


def downgrade():
    nombres = {
        "politicas_servicio": ("ck_politica_max_positivo", "ck_politica_dias_positivo",
                                "ck_politica_gracia_no_negativa", "ck_politica_tipos_no_vacios"),
        "usuarios": ("ck_usuario_nombre_no_vacio", "ck_usuario_correo_canonico",
                     "ck_usuario_correo_no_vacio"),
        "perfiles_estudiante": ("ck_estudiante_codigo_no_vacio",),
        "perfiles_docente": ("ck_docente_codigo_no_vacio", "ck_docente_contrato_no_vacio"),
        "perfiles_administrativo": ("ck_administrativo_codigo_no_vacio",
                                     "ck_administrativo_cargo_no_vacio"),
        "perfiles_gestor_inventario": ("ck_gestor_codigo_no_vacio", "ck_gestor_area_no_vacia"),
        "items": ("ck_item_codigo_canonico", "ck_item_codigo_no_vacio",
                  "ck_item_nombre_no_vacio", "ck_item_categoria_no_vacia",
                  "ck_item_tipo_no_vacio", "ck_item_estado_valido"),
        "prestamos": ("ck_prestamo_fechas_ordenadas",),
    }
    for tabla, restricciones in nombres.items():
        with op.batch_alter_table(tabla) as lote:
            for nombre in restricciones:
                lote.drop_constraint(nombre, type_="check")
