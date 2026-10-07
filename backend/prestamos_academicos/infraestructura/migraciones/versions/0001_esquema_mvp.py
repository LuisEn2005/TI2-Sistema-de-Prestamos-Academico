"""Esquema del MVP (Sprint 1): usuarios, recursos y préstamos.

Es idempotente: si la base ya fue creada por el MVP sin Alembic, no toca las tablas.

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    if "usuarios" not in existentes:
        op.create_table(
            "usuarios",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("nombre", sa.String(120), nullable=False),
        )
    if "recursos" not in existentes:
        op.create_table(
            "recursos",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("codigo", sa.String(30), nullable=False, unique=True),
            sa.Column("nombre", sa.String(120), nullable=False),
            sa.Column("tipo", sa.String(30), nullable=False),
            sa.Column("disponible", sa.Boolean, nullable=False, server_default=sa.true()),
        )
    if "prestamos" not in existentes:
        op.create_table(
            "prestamos",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False),
            sa.Column("recurso_id", sa.Integer, sa.ForeignKey("recursos.id"), nullable=False),
            sa.Column("fecha_prestamo", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),
            sa.Column("fecha_devolucion", sa.DateTime(timezone=True)),
        )


def downgrade():
    raise NotImplementedError("No se revierte el esquema base del MVP.")
