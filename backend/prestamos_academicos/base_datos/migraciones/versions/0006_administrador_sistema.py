"""Separa la administración del rol operativo de inventario.

Revision ID: 0006
Revises: 0005
"""

from alembic import op
import sqlalchemy as sa


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "perfiles_administrador_sistema",
        sa.Column("usuario_id", sa.Integer,
                  sa.ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("codigo_empleado", sa.String(30), nullable=False, unique=True),
        sa.Column("fecha_asignacion", sa.Date, nullable=False,
                  server_default=sa.func.current_date()),
        sa.CheckConstraint("length(trim(codigo_empleado)) > 0",
                           name="ck_admin_sistema_codigo_no_vacio"),
    )
    # Conserva el acceso administrativo de instalaciones anteriores. Se elige
    # de forma determinista el gestor activo más antiguo y mantiene su rol
    # operativo para no alterar sus tareas actuales.
    op.execute("""
        INSERT INTO perfiles_administrador_sistema
            (usuario_id, codigo_empleado, fecha_asignacion)
        SELECT g.usuario_id, g.codigo_empleado, CURRENT_DATE
        FROM perfiles_gestor_inventario g
        JOIN usuarios u ON u.id = g.usuario_id
        WHERE u.activo = true
        ORDER BY g.usuario_id
        LIMIT 1
    """)


def downgrade():
    op.drop_table("perfiles_administrador_sistema")
