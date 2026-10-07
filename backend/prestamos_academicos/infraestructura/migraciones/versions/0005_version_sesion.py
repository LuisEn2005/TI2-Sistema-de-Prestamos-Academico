"""Permite revocar sesiones al cambiar credenciales o activar cuentas.

Revision ID: 0005
Revises: 0004
"""

from alembic import op
import sqlalchemy as sa


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("usuarios") as lote:
        lote.add_column(sa.Column("version_sesion", sa.Integer, nullable=False,
                                  server_default="0"))
        lote.create_check_constraint("ck_usuario_version_sesion_no_negativa",
                                     "version_sesion >= 0")


def downgrade():
    with op.batch_alter_table("usuarios") as lote:
        lote.drop_constraint("ck_usuario_version_sesion_no_negativa", type_="check")
        lote.drop_column("version_sesion")
