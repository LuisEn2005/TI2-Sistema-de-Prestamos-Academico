"""Agrega rangos de reserva y calendario institucional.

Revision ID: 0014
Revises: 0013
"""

from alembic import op
import sqlalchemy as sa


revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("ux_reserva_item_activa", table_name="reservas")
    with op.batch_alter_table("reservas") as lote:
        lote.alter_column("fecha_reserva", new_column_name="fecha_inicio")
        lote.add_column(sa.Column("fecha_fin", sa.Date))
        lote.add_column(sa.Column("modalidad_id", sa.Integer))
        lote.add_column(sa.Column("confirmada_por_usuario_id", sa.Integer))
        lote.add_column(sa.Column("confirmada_en", sa.DateTime(timezone=True)))
        lote.add_column(sa.Column("motivo_resolucion", sa.String(300)))
        lote.create_foreign_key(
            "fk_reserva_modalidad", "modalidades", ["modalidad_id"], ["id"])
        lote.create_foreign_key(
            "fk_reserva_confirmada_por", "usuarios",
            ["confirmada_por_usuario_id"], ["id"])
        lote.drop_constraint("ck_reserva_estado_valido", type_="check")
        lote.create_check_constraint(
            "ck_reserva_estado_valido",
            "estado IN ('PENDIENTE','CONFIRMADA','EXPIRADA','CANCELADA',"
            "'CONVERTIDA','RECHAZADA')")

    op.execute(sa.text("UPDATE reservas SET fecha_fin = fecha_inicio"))
    with op.batch_alter_table("reservas") as lote:
        lote.alter_column("fecha_fin", nullable=False)
        lote.create_check_constraint(
            "ck_reserva_fechas_ordenadas", "fecha_fin >= fecha_inicio")
        lote.create_index(
            "ix_reservas_item_fechas", ["item_id", "fecha_inicio", "fecha_fin"])

    with op.batch_alter_table("prestamos") as lote:
        lote.add_column(sa.Column(
            "dias_aplazados", sa.Integer, nullable=False, server_default="0"))
        lote.create_check_constraint(
            "ck_prestamo_aplazamiento_no_negativo", "dias_aplazados >= 0")

    op.create_table(
        "dias_no_laborables",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("fecha_inicio", sa.Date, nullable=False),
        sa.Column("fecha_fin", sa.Date, nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("motivo", sa.String(200), nullable=False),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("creado_por_usuario_id", sa.Integer, sa.ForeignKey("usuarios.id"),
                  nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("fecha_fin >= fecha_inicio", name="ck_cierre_fechas_ordenadas"),
        sa.CheckConstraint(
            "tipo IN ('FERIADO','HUELGA','OTRO')", name="ck_cierre_tipo_valido"),
    )
    op.create_index(
        "ix_dias_no_laborables_fechas", "dias_no_laborables",
        ["fecha_inicio", "fecha_fin", "activo"])

    # Las reservas pasan a ser disponibilidad por fecha, no un estado físico permanente.
    op.execute(sa.text("UPDATE items SET estado = 'DISPONIBLE' WHERE estado = 'RESERVADO'"))

    # Se respeta cualquier personalización distinta del valor inicial de 15 días.
    op.execute(sa.text("""
        UPDATE politicas_servicio
        SET dias_prestamo = 14
        WHERE dias_prestamo = 15
          AND rol_aplicable IN ('DOCENTE', 'ADMINISTRATIVO')
          AND modalidad_id IN (
              SELECT id FROM modalidades WHERE nombre = 'Externa (a domicilio)'
          )
    """))


def downgrade():
    op.execute(sa.text("""
        UPDATE politicas_servicio
        SET dias_prestamo = 15
        WHERE dias_prestamo = 14
          AND rol_aplicable IN ('DOCENTE', 'ADMINISTRATIVO')
          AND modalidad_id IN (
              SELECT id FROM modalidades WHERE nombre = 'Externa (a domicilio)'
          )
    """))
    op.drop_index("ix_dias_no_laborables_fechas", table_name="dias_no_laborables")
    op.drop_table("dias_no_laborables")
    with op.batch_alter_table("prestamos") as lote:
        lote.drop_constraint("ck_prestamo_aplazamiento_no_negativo", type_="check")
        lote.drop_column("dias_aplazados")
    op.drop_index("ix_reservas_item_fechas", table_name="reservas")
    with op.batch_alter_table("reservas") as lote:
        lote.drop_constraint("ck_reserva_fechas_ordenadas", type_="check")
        lote.drop_constraint("fk_reserva_confirmada_por", type_="foreignkey")
        lote.drop_constraint("fk_reserva_modalidad", type_="foreignkey")
        lote.drop_constraint("ck_reserva_estado_valido", type_="check")
        lote.create_check_constraint(
            "ck_reserva_estado_valido",
            "estado IN ('PENDIENTE','CONFIRMADA','EXPIRADA','CANCELADA','CONVERTIDA')")
        lote.drop_column("motivo_resolucion")
        lote.drop_column("confirmada_en")
        lote.drop_column("confirmada_por_usuario_id")
        lote.drop_column("modalidad_id")
        lote.drop_column("fecha_fin")
        lote.alter_column("fecha_inicio", new_column_name="fecha_reserva")
        lote.create_index(
            "ux_reserva_item_activa", ["item_id"], unique=True,
            sqlite_where=sa.text("estado IN ('PENDIENTE','CONFIRMADA')"),
            postgresql_where=sa.text("estado IN ('PENDIENTE','CONFIRMADA')"))
