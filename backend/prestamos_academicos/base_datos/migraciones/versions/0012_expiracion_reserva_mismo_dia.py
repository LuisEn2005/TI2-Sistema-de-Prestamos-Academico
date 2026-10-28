"""Hace que toda reserva expire al terminar el día reservado.

Revision ID: 0012
Revises: 0011
"""

from alembic import op
import sqlalchemy as sa


revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    # La expiración ya se deriva de fecha_reserva; guardar otra fecha sería redundante.
    with op.batch_alter_table("reservas") as lote:
        lote.drop_constraint("ck_reserva_fechas_ordenadas", type_="check")
        lote.drop_column("fecha_expiracion")

    # La regla es igual para todos los roles y deja de ser parte de la política.
    with op.batch_alter_table("politicas_servicio") as lote:
        lote.drop_constraint("ck_politica_gracia_no_negativa", type_="check")
        lote.drop_column("dias_gracia_reserva")


def downgrade():
    # Al volver, cero días de gracia reproduce exactamente la regla actual.
    with op.batch_alter_table("politicas_servicio") as lote:
        lote.add_column(sa.Column(
            "dias_gracia_reserva", sa.Integer, nullable=False, server_default="0"))
        lote.create_check_constraint(
            "ck_politica_gracia_no_negativa", "dias_gracia_reserva >= 0")

    with op.batch_alter_table("reservas") as lote:
        lote.add_column(sa.Column("fecha_expiracion", sa.Date, nullable=True))
    op.execute("UPDATE reservas SET fecha_expiracion = fecha_reserva")
    with op.batch_alter_table("reservas") as lote:
        lote.alter_column("fecha_expiracion", existing_type=sa.Date, nullable=False)
        lote.create_check_constraint(
            "ck_reserva_fechas_ordenadas", "fecha_expiracion >= fecha_reserva")
