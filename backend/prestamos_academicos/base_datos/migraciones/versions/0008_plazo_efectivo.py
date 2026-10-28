"""Conserva el plazo efectivo aplicado a cada préstamo.

El plazo de la modalidad es un máximo. El valor realmente aplicado depende de
la política del perfil y debe persistirse para no confundir ambos conceptos.

Revision ID: 0008
Revises: 0007
"""

from alembic import op
import sqlalchemy as sa


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("prestamos") as lote:
        lote.add_column(sa.Column("dias_plazo_aplicado", sa.Integer))
        lote.create_check_constraint(
            "ck_prestamo_plazo_aplicado_positivo",
            "dias_plazo_aplicado IS NULL OR dias_plazo_aplicado > 0",
        )

    # Los préstamos del Sprint 3 ya tienen las fechas necesarias para recuperar
    # su plazo efectivo. Los heredados del MVP conservan NULL porque no tenían
    # fecha límite ni modalidad.
    prestamos = sa.table(
        "prestamos",
        sa.column("id", sa.Integer),
        sa.column("fecha_prestamo", sa.DateTime(timezone=True)),
        sa.column("fecha_devolucion_esperada", sa.Date),
        sa.column("dias_plazo_aplicado", sa.Integer),
    )
    bind = op.get_bind()
    filas = bind.execute(sa.select(
        prestamos.c.id,
        prestamos.c.fecha_prestamo,
        prestamos.c.fecha_devolucion_esperada,
    )).all()
    for prestamo_id, fecha_entrega, fecha_limite in filas:
        if fecha_entrega is None or fecha_limite is None:
            continue
        dias = (fecha_limite - fecha_entrega.date()).days
        if dias > 0:
            bind.execute(
                prestamos.update().where(prestamos.c.id == prestamo_id).values(
                    dias_plazo_aplicado=dias),
            )

    # La modalidad indica el máximo. Con 15 días, la política aplica 7 al
    # estudiante y 15 al docente también en el flujo in situ.
    bind.execute(sa.text("""
        UPDATE modalidades SET dias_plazo_default = 15
        WHERE nombre = :nombre AND dias_plazo_default = 1
    """).bindparams(sa.bindparam("nombre", type_=sa.String(60))), {
        "nombre": "In situ (en sala)",
    })


def downgrade():
    op.execute("""
        UPDATE modalidades SET dias_plazo_default = 1
        WHERE nombre = 'In situ (en sala)' AND dias_plazo_default = 15
    """)
    with op.batch_alter_table("prestamos") as lote:
        lote.drop_constraint("ck_prestamo_plazo_aplicado_positivo", type_="check")
        lote.drop_column("dias_plazo_aplicado")
