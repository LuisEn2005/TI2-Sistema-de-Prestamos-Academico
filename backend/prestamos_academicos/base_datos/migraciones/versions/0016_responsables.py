"""Registra quién entregó y recibió cada préstamo y quién cerró cada sanción.

Revision ID: 0016
Revises: 0015
"""

from alembic import op
import sqlalchemy as sa


revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("prestamos") as lote:
        lote.add_column(sa.Column("entregado_por_usuario_id", sa.Integer(),
                                  sa.ForeignKey("usuarios.id", name="fk_prestamo_entregado_por")))
        lote.add_column(sa.Column("recibido_por_usuario_id", sa.Integer(),
                                  sa.ForeignKey("usuarios.id", name="fk_prestamo_recibido_por")))
    with op.batch_alter_table("sanciones") as lote:
        lote.add_column(sa.Column("cerrada_por_usuario_id", sa.Integer(),
                                  sa.ForeignKey("usuarios.id", name="fk_sancion_cerrada_por")))


def downgrade():
    with op.batch_alter_table("sanciones") as lote:
        lote.drop_column("cerrada_por_usuario_id")
    with op.batch_alter_table("prestamos") as lote:
        lote.drop_column("recibido_por_usuario_id")
        lote.drop_column("entregado_por_usuario_id")
