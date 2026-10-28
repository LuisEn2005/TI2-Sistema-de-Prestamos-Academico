"""Sprint 4: reservas, conversión en préstamo y renovaciones.

Revision ID: 0009
Revises: 0008
"""

from alembic import op
import sqlalchemy as sa


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reservas",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("items.id"), nullable=False),
        sa.Column("rol_solicitante", sa.String(30), nullable=False),
        sa.Column("fecha_solicitud", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("fecha_reserva", sa.Date, nullable=False),
        sa.Column("fecha_expiracion", sa.Date, nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="PENDIENTE"),
        sa.CheckConstraint(
            "rol_solicitante IN ('ESTUDIANTE','DOCENTE','ADMINISTRATIVO')",
            name="ck_reserva_rol_valido"),
        sa.CheckConstraint(
            "estado IN ('PENDIENTE','CONFIRMADA','EXPIRADA','CANCELADA','CONVERTIDA')",
            name="ck_reserva_estado_valido"),
        sa.CheckConstraint(
            "fecha_expiracion >= fecha_reserva", name="ck_reserva_fechas_ordenadas"),
    )
    op.create_index("ix_reservas_usuario_estado", "reservas", ["usuario_id", "estado"])
    op.create_index("ix_reservas_item_estado", "reservas", ["item_id", "estado"])
    op.create_index(
        "ux_reserva_item_activa", "reservas", ["item_id"], unique=True,
        sqlite_where=sa.text("estado IN ('PENDIENTE','CONFIRMADA')"),
        postgresql_where=sa.text("estado IN ('PENDIENTE','CONFIRMADA')"),
    )

    with op.batch_alter_table("prestamos") as lote:
        lote.add_column(sa.Column(
            "numero_renovaciones", sa.Integer, nullable=False, server_default="0"))
        lote.add_column(sa.Column("reserva_id", sa.Integer))
        lote.create_check_constraint(
            "ck_prestamo_renovaciones_no_negativas", "numero_renovaciones >= 0")
        lote.create_foreign_key(
            "fk_prestamos_reserva", "reservas", ["reserva_id"], ["id"])
        lote.create_unique_constraint("uq_prestamos_reserva", ["reserva_id"])


def downgrade():
    with op.batch_alter_table("prestamos") as lote:
        lote.drop_constraint("uq_prestamos_reserva", type_="unique")
        lote.drop_constraint("fk_prestamos_reserva", type_="foreignkey")
        lote.drop_constraint("ck_prestamo_renovaciones_no_negativas", type_="check")
        lote.drop_column("reserva_id")
        lote.drop_column("numero_renovaciones")
    op.drop_index("ux_reserva_item_activa", table_name="reservas")
    op.drop_index("ix_reservas_item_estado", table_name="reservas")
    op.drop_index("ix_reservas_usuario_estado", table_name="reservas")
    op.drop_table("reservas")
