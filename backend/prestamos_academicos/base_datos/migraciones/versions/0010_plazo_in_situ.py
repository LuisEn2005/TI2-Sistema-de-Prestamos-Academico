"""Fija el préstamo in situ hasta el final del día de la entrega.

Revision ID: 0010
Revises: 0009
"""

from alembic import op
import sqlalchemy as sa


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def _actualizar_plazo(origen: int, destino: int) -> None:
    modalidades = sa.table(
        "modalidades",
        sa.column("nombre", sa.String(60)),
        sa.column("dias_plazo_default", sa.Integer),
    )
    op.get_bind().execute(
        modalidades.update().where(
            modalidades.c.nombre == "In situ (en sala)",
            modalidades.c.dias_plazo_default == origen,
        ).values(dias_plazo_default=destino)
    )


def upgrade():
    _actualizar_plazo(15, 1)


def downgrade():
    _actualizar_plazo(1, 15)
