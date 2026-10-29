"""Implementa sanciones y reglas de sancion configurables.

Revision ID: 0013
Revises: 0012
"""

from alembic import op
import sqlalchemy as sa


revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("politicas_servicio") as lote:
        lote.add_column(sa.Column(
            "dias_sancion_por_dia_atraso", sa.Integer,
            nullable=False, server_default="1"))
        lote.create_check_constraint(
            "ck_politica_sancion_positiva", "dias_sancion_por_dia_atraso > 0")

    op.create_table(
        "sanciones",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("prestamo_id", sa.Integer, sa.ForeignKey("prestamos.id")),
        sa.Column("creada_por_usuario_id", sa.Integer, sa.ForeignKey("usuarios.id")),
        sa.Column("origen", sa.String(20), nullable=False),
        sa.Column("motivo", sa.String(300), nullable=False),
        sa.Column("monto", sa.Numeric(10, 2)),
        sa.Column("moneda", sa.String(3)),
        sa.Column("fecha_inicio", sa.Date, nullable=False),
        sa.Column("fecha_fin", sa.Date),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("cerrada_en", sa.DateTime(timezone=True)),
        sa.Column("resolucion", sa.String(300)),
        sa.CheckConstraint(
            "origen IN ('RETRASO','DANO','PERDIDA')", name="ck_sancion_origen_valido"),
        sa.CheckConstraint(
            "estado IN ('ACTIVA','CERRADA')", name="ck_sancion_estado_valido"),
        sa.CheckConstraint(
            "fecha_fin IS NULL OR fecha_fin >= fecha_inicio",
            name="ck_sancion_fechas_ordenadas"),
        sa.CheckConstraint("monto IS NULL OR monto > 0", name="ck_sancion_monto_positivo"),
        sa.CheckConstraint(
            "(monto IS NULL AND moneda IS NULL) OR (monto IS NOT NULL AND moneda IS NOT NULL)",
            name="ck_sancion_monto_moneda"),
    )
    op.create_index("ix_sanciones_usuario_estado", "sanciones", ["usuario_id", "estado"])
    op.create_index("ix_sanciones_prestamo", "sanciones", ["prestamo_id"])


def downgrade():
    op.drop_index("ix_sanciones_prestamo", table_name="sanciones")
    op.drop_index("ix_sanciones_usuario_estado", table_name="sanciones")
    op.drop_table("sanciones")
    with op.batch_alter_table("politicas_servicio") as lote:
        lote.drop_constraint("ck_politica_sancion_positiva", type_="check")
        lote.drop_column("dias_sancion_por_dia_atraso")
