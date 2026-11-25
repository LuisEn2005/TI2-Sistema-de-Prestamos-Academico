"""Vincula opcionalmente una sanción manual con el recurso dañado o perdido.

Revision ID: 0017
Revises: 0016
"""

from alembic import op
import sqlalchemy as sa


revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("sanciones") as lote:
        lote.add_column(sa.Column("item_id", sa.Integer(),
                                  sa.ForeignKey("items.id", name="fk_sancion_item")))


def downgrade():
    with op.batch_alter_table("sanciones") as lote:
        lote.drop_column("item_id")
