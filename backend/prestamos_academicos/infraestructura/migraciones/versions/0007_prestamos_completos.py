"""Sprint 3: préstamos con varios ítems, modalidades, fecha límite y condición de devolución.

- Crea `modalidades` y `detalles_prestamo`.
- Cada préstamo existente pasa a tener un detalle con su ítem (activo si aún no se devolvió).
  Los préstamos anteriores no tenían modalidad, rol ni fecha límite: esos campos quedan en
  NULL y la condición de devolución de los ya devueltos queda sin registrar.
- Elimina `prestamos.item_id` (ahora vive en el detalle).

Revision ID: 0007
Revises: 0006
"""

from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "modalidades",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nombre", sa.String(60), nullable=False, unique=True),
        sa.Column("dias_plazo_default", sa.Integer, nullable=False),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.CheckConstraint("length(trim(nombre)) > 0", name="ck_modalidad_nombre_no_vacio"),
        sa.CheckConstraint("dias_plazo_default > 0", name="ck_modalidad_dias_positivo"),
    )

    op.create_table(
        "detalles_prestamo",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("prestamo_id", sa.Integer,
                  sa.ForeignKey("prestamos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("items.id"), nullable=False),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("condicion", sa.String(20)),
        sa.Column("observacion", sa.String(300)),
        sa.UniqueConstraint("prestamo_id", "item_id", name="uq_detalle_prestamo_item"),
        sa.CheckConstraint(
            "condicion IS NULL OR condicion IN ('BUEN_ESTADO','DANADO','PERDIDO')",
            name="ck_detalle_condicion_valida"),
    )
    op.create_index("ix_detalles_prestamo", "detalles_prestamo", ["prestamo_id"])
    op.create_index("ux_detalles_item_activo", "detalles_prestamo", ["item_id"], unique=True,
                    sqlite_where=sa.text("activo"), postgresql_where=sa.text("activo"))

    op.execute("""
        INSERT INTO detalles_prestamo (prestamo_id, item_id, activo)
        SELECT id, item_id, (fecha_devolucion IS NULL) FROM prestamos
    """)

    with op.batch_alter_table("prestamos") as lote:
        lote.add_column(sa.Column("rol_solicitante", sa.String(30)))
        lote.add_column(sa.Column("modalidad_id", sa.Integer))
        lote.add_column(sa.Column("modalidad_nombre", sa.String(60)))
        lote.add_column(sa.Column("modalidad_dias_plazo", sa.Integer))
        lote.add_column(sa.Column("fecha_devolucion_esperada", sa.Date))
        lote.drop_column("item_id")
        lote.create_foreign_key("fk_prestamos_modalidad", "modalidades",
                                ["modalidad_id"], ["id"])
        lote.create_check_constraint("ck_prestamo_plazo_positivo",
                                     "modalidad_dias_plazo IS NULL OR modalidad_dias_plazo > 0")
        lote.create_check_constraint(
            "ck_prestamo_rol_valido",
            "rol_solicitante IS NULL OR rol_solicitante IN ('ESTUDIANTE','DOCENTE','ADMINISTRATIVO')")
        lote.create_index("ix_prestamos_usuario", ["usuario_id"])


def downgrade():
    # Solo se conserva el primer ítem de cada préstamo: el esquema anterior admite uno.
    with op.batch_alter_table("prestamos") as lote:
        lote.drop_index("ix_prestamos_usuario")
        lote.drop_constraint("ck_prestamo_rol_valido", type_="check")
        lote.drop_constraint("ck_prestamo_plazo_positivo", type_="check")
        lote.drop_constraint("fk_prestamos_modalidad", type_="foreignkey")
        lote.add_column(sa.Column("item_id", sa.Integer))
    op.execute("""
        UPDATE prestamos SET item_id = (
            SELECT MIN(d.item_id) FROM detalles_prestamo d WHERE d.prestamo_id = prestamos.id)
    """)
    with op.batch_alter_table("prestamos") as lote:
        lote.alter_column("item_id", existing_type=sa.Integer, nullable=False)
        lote.create_foreign_key("fk_prestamos_item", "items", ["item_id"], ["id"])
        lote.drop_column("fecha_devolucion_esperada")
        lote.drop_column("modalidad_dias_plazo")
        lote.drop_column("modalidad_nombre")
        lote.drop_column("modalidad_id")
        lote.drop_column("rol_solicitante")
    op.drop_index("ux_detalles_item_activo", table_name="detalles_prestamo")
    op.drop_index("ix_detalles_prestamo", table_name="detalles_prestamo")
    op.drop_table("detalles_prestamo")
    op.drop_table("modalidades")
