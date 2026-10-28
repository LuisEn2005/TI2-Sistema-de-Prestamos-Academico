"""Normaliza modalidades, políticas, tipos permitidos y préstamos.

Revision ID: 0011
Revises: 0010
"""

from alembic import op
import sqlalchemy as sa


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


TIPOS_BASE = {
    "LIBRO": "Libro",
    "EQUIPO": "Equipo",
    "MATERIAL": "Material",
    "MOBILIARIO": "Mobiliario",
}
ROLES_PRESTATARIOS = ("ESTUDIANTE", "DOCENTE", "ADMINISTRATIVO")


def upgrade():
    bind = op.get_bind()

    # Catálogo referenciado tanto por inventario como por las políticas (1FN).
    op.create_table(
        "tipos_recurso",
        sa.Column("codigo", sa.String(30), primary_key=True),
        sa.Column("nombre", sa.String(80), nullable=False, unique=True),
    )
    tipos = sa.table(
        "tipos_recurso", sa.column("codigo", sa.String(30)),
        sa.column("nombre", sa.String(80)))
    for codigo, nombre in TIPOS_BASE.items():
        bind.execute(tipos.insert().values(codigo=codigo, nombre=nombre))

    with op.batch_alter_table("items") as lote:
        lote.create_foreign_key(
            "fk_items_tipo_recurso", "tipos_recurso", ["tipo"], ["codigo"])

    # Un perfil representa la vinculación de la persona; la política se resuelve
    # por rol + modalidad y ya no pertenece a una fila de perfil.
    for tabla in ("perfiles_estudiante", "perfiles_docente", "perfiles_administrativo"):
        with op.batch_alter_table(tabla) as lote:
            lote.drop_column("politica_servicio_id")

    # Una instalación migrada puede no haber ejecutado todavía el sembrado de la app.
    modalidades = sa.table(
        "modalidades",
        sa.column("id", sa.Integer), sa.column("nombre", sa.String(60)),
        sa.column("dias_plazo_default", sa.Integer), sa.column("activo", sa.Boolean))
    nombres_modalidad = set(bind.execute(sa.select(modalidades.c.nombre)).scalars())
    for nombre, dias in (("In situ (en sala)", 1), ("Externa (a domicilio)", 15)):
        if nombre not in nombres_modalidad:
            bind.execute(modalidades.insert().values(
                nombre=nombre, dias_plazo_default=dias, activo=True))

    # Se conserva la tabla anterior mientras sus filas se expanden a una política
    # por cada combinación rol-modalidad.
    op.create_table(
        "politicas_servicio_nueva",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("rol_aplicable", sa.String(30), nullable=False),
        sa.Column("modalidad_id", sa.Integer, sa.ForeignKey("modalidades.id"), nullable=False),
        sa.Column("max_items_simultaneos", sa.Integer, nullable=False),
        sa.Column("dias_prestamo", sa.Integer, nullable=False),
        sa.Column("dias_gracia_reserva", sa.Integer, nullable=False),
        sa.UniqueConstraint("rol_aplicable", "modalidad_id",
                            name="uq_politica_rol_modalidad"),
        sa.CheckConstraint(
            "rol_aplicable IN ('ESTUDIANTE','DOCENTE','ADMINISTRATIVO')",
            name="ck_politica_rol_valido"),
        sa.CheckConstraint("max_items_simultaneos > 0", name="ck_politica_max_positivo"),
        sa.CheckConstraint("dias_prestamo > 0", name="ck_politica_dias_positivo"),
        sa.CheckConstraint("dias_gracia_reserva >= 0",
                           name="ck_politica_gracia_no_negativa"),
    )
    op.create_table(
        "politica_tipos_recurso",
        sa.Column("politica_servicio_id", sa.Integer,
                  sa.ForeignKey("politicas_servicio_nueva.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("tipo_recurso_codigo", sa.String(30),
                  sa.ForeignKey("tipos_recurso.codigo"), primary_key=True),
    )

    legacy = sa.table(
        "politicas_servicio",
        sa.column("rol_aplicable", sa.String(30)),
        sa.column("max_items_simultaneos", sa.Integer),
        sa.column("dias_prestamo_default", sa.Integer),
        sa.column("dias_gracia_reserva", sa.Integer),
        sa.column("tipos_recurso_permitidos", sa.String(200)),
    )
    nuevas = sa.table(
        "politicas_servicio_nueva",
        sa.column("id", sa.Integer), sa.column("rol_aplicable", sa.String(30)),
        sa.column("modalidad_id", sa.Integer),
        sa.column("max_items_simultaneos", sa.Integer),
        sa.column("dias_prestamo", sa.Integer),
        sa.column("dias_gracia_reserva", sa.Integer),
    )
    relaciones = sa.table(
        "politica_tipos_recurso",
        sa.column("politica_servicio_id", sa.Integer),
        sa.column("tipo_recurso_codigo", sa.String(30)),
    )
    filas_modalidad = bind.execute(sa.select(
        modalidades.c.id, modalidades.c.nombre).order_by(modalidades.c.id)).all()
    filas_legacy = bind.execute(sa.select(legacy)).mappings().all()
    for anterior in filas_legacy:
        if anterior["rol_aplicable"] not in ROLES_PRESTATARIOS:
            continue
        permitidos = [
            tipo.strip().upper()
            for tipo in (anterior["tipos_recurso_permitidos"] or "").split(",")
            if tipo.strip()
        ]
        for codigo in permitidos:
            if bind.scalar(sa.select(sa.func.count()).select_from(tipos).where(
                    tipos.c.codigo == codigo)) == 0:
                bind.execute(tipos.insert().values(codigo=codigo, nombre=codigo.title()))
        for modalidad_id, modalidad_nombre in filas_modalidad:
            dias = 1 if modalidad_nombre == "In situ (en sala)" else anterior[
                "dias_prestamo_default"]
            politica_id = bind.execute(nuevas.insert().values(
                rol_aplicable=anterior["rol_aplicable"],
                modalidad_id=modalidad_id,
                max_items_simultaneos=anterior["max_items_simultaneos"],
                dias_prestamo=dias,
                dias_gracia_reserva=anterior["dias_gracia_reserva"],
            ).returning(nuevas.c.id)).scalar_one()
            for codigo in permitidos:
                bind.execute(relaciones.insert().values(
                    politica_servicio_id=politica_id,
                    tipo_recurso_codigo=codigo,
                ))

    # El préstamo conserva solo FKs y el plazo histórico efectivamente otorgado.
    with op.batch_alter_table("prestamos") as lote:
        lote.add_column(sa.Column("politica_servicio_id", sa.Integer))
        lote.drop_constraint("ck_prestamo_plazo_aplicado_positivo", type_="check")
        lote.alter_column(
            "dias_plazo_aplicado", new_column_name="dias_plazo",
            existing_type=sa.Integer, existing_nullable=True)
        lote.create_check_constraint(
            "ck_prestamo_dias_plazo_positivo", "dias_plazo IS NULL OR dias_plazo > 0")

    prestamos = sa.table(
        "prestamos",
        sa.column("id", sa.Integer), sa.column("rol_solicitante", sa.String(30)),
        sa.column("modalidad_id", sa.Integer),
        sa.column("politica_servicio_id", sa.Integer),
    )
    for prestamo_id, rol, modalidad_id in bind.execute(sa.select(
            prestamos.c.id, prestamos.c.rol_solicitante,
            prestamos.c.modalidad_id)).all():
        if not rol or not modalidad_id:
            continue
        politica_id = bind.scalar(sa.select(nuevas.c.id).where(
            nuevas.c.rol_aplicable == rol,
            nuevas.c.modalidad_id == modalidad_id,
        ))
        if politica_id:
            bind.execute(prestamos.update().where(
                prestamos.c.id == prestamo_id).values(
                    politica_servicio_id=politica_id))

    with op.batch_alter_table("prestamos") as lote:
        lote.drop_constraint("ck_prestamo_plazo_positivo", type_="check")
        lote.drop_constraint("ck_prestamo_rol_valido", type_="check")
        lote.drop_column("modalidad_nombre")
        lote.drop_column("modalidad_dias_plazo")
        lote.drop_column("rol_solicitante")

    op.drop_table("politicas_servicio")
    op.rename_table("politicas_servicio_nueva", "politicas_servicio")
    with op.batch_alter_table("prestamos") as lote:
        lote.create_foreign_key(
            "fk_prestamos_politica", "politicas_servicio",
            ["politica_servicio_id"], ["id"])

    with op.batch_alter_table("modalidades") as lote:
        lote.drop_constraint("ck_modalidad_dias_positivo", type_="check")
        lote.drop_column("dias_plazo_default")


def downgrade():
    raise NotImplementedError(
        "La normalización 0011 consolida relaciones y no se revierte automáticamente.")
