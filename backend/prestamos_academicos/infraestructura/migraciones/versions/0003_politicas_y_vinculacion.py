"""Completa políticas heredadas y registra la vinculación del personal.

Revision ID: 0003
Revises: 0002
"""

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


POLITICAS = (
    ("ESTUDIANTE", 3, 7, 2, "LIBRO,EQUIPO,MATERIAL"),
    ("DOCENTE", 5, 15, 3, "LIBRO,EQUIPO,MATERIAL,MOBILIARIO"),
    ("ADMINISTRATIVO", 5, 15, 3, "LIBRO,EQUIPO,MATERIAL,MOBILIARIO"),
)


def upgrade():
    bind = op.get_bind()

    # Alembic se ejecuta antes que la carga de configuración. La migración debe
    # poder reparar por sí sola una base heredada que todavía no tiene políticas.
    for rol, maximos, dias, gracia, tipos in POLITICAS:
        bind.execute(sa.text("""
            INSERT INTO politicas_servicio (
                rol_aplicable, max_items_simultaneos, dias_prestamo_default,
                dias_gracia_reserva, tipos_recurso_permitidos
            )
            SELECT :rol, :maximos, :dias, :gracia, :tipos
            WHERE NOT EXISTS (
                SELECT 1 FROM politicas_servicio WHERE rol_aplicable = :rol
            )
        """), {"rol": rol, "maximos": maximos, "dias": dias,
               "gracia": gracia, "tipos": tipos})

    for tabla, rol in (
        ("perfiles_estudiante", "ESTUDIANTE"),
        ("perfiles_docente", "DOCENTE"),
        ("perfiles_administrativo", "ADMINISTRATIVO"),
    ):
        bind.execute(sa.text(f"""
            UPDATE {tabla}
            SET politica_servicio_id = (
                SELECT id FROM politicas_servicio WHERE rol_aplicable = :rol
            )
            WHERE politica_servicio_id IS NULL
        """), {"rol": rol})

    with op.batch_alter_table("perfiles_docente") as lote:
        lote.add_column(sa.Column("vinculacion_vigente", sa.Boolean,
                                  nullable=False, server_default=sa.true()))
    with op.batch_alter_table("perfiles_administrativo") as lote:
        lote.add_column(sa.Column("vinculacion_vigente", sa.Boolean,
                                  nullable=False, server_default=sa.true()))

    for tabla in ("perfiles_estudiante", "perfiles_docente", "perfiles_administrativo"):
        with op.batch_alter_table(tabla) as lote:
            lote.alter_column("politica_servicio_id", existing_type=sa.Integer,
                              existing_nullable=True, nullable=False)


def downgrade():
    for tabla in ("perfiles_estudiante", "perfiles_docente", "perfiles_administrativo"):
        with op.batch_alter_table(tabla) as lote:
            lote.alter_column("politica_servicio_id", existing_type=sa.Integer,
                              existing_nullable=False, nullable=True)
    with op.batch_alter_table("perfiles_administrativo") as lote:
        lote.drop_column("vinculacion_vigente")
    with op.batch_alter_table("perfiles_docente") as lote:
        lote.drop_column("vinculacion_vigente")
