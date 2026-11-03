"""Separa políticas por rol y agrega trazabilidad operativa.

Revision ID: 0015
Revises: 0014
"""

from alembic import op
import sqlalchemy as sa


revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


ROLES = ("ESTUDIANTE", "DOCENTE", "ADMINISTRATIVO")


def upgrade():
    bind = op.get_bind()
    op.create_table(
        "politicas_rol",
        sa.Column("rol", sa.String(30), primary_key=True),
        sa.Column("max_items_simultaneos", sa.Integer(), nullable=False),
        sa.Column("dias_sancion_por_dia_atraso", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "rol IN ('ESTUDIANTE','DOCENTE','ADMINISTRATIVO')",
            name="ck_politica_rol_perfil_valido"),
        sa.CheckConstraint("max_items_simultaneos > 0", name="ck_politica_rol_max_positivo"),
        sa.CheckConstraint(
            "dias_sancion_por_dia_atraso > 0",
            name="ck_politica_rol_sancion_positiva"),
    )
    politicas = sa.table(
        "politicas_servicio",
        sa.column("rol_aplicable", sa.String(30)),
        sa.column("max_items_simultaneos", sa.Integer()),
        sa.column("dias_sancion_por_dia_atraso", sa.Integer()),
    )
    reglas = sa.table(
        "politicas_rol",
        sa.column("rol", sa.String(30)),
        sa.column("max_items_simultaneos", sa.Integer()),
        sa.column("dias_sancion_por_dia_atraso", sa.Integer()),
    )
    for rol in ROLES:
        fila = bind.execute(
            sa.select(
                sa.func.min(politicas.c.max_items_simultaneos),
                sa.func.max(politicas.c.dias_sancion_por_dia_atraso),
            ).where(politicas.c.rol_aplicable == rol)
        ).first()
        maximo, sancion = fila if fila and fila[0] is not None else (
            (3 if rol == "ESTUDIANTE" else 5), 1)
        bind.execute(reglas.insert().values(
            rol=rol, max_items_simultaneos=maximo,
            dias_sancion_por_dia_atraso=sancion))

    with op.batch_alter_table("politicas_servicio") as lote:
        lote.drop_constraint("ck_politica_max_positivo", type_="check")
        lote.drop_constraint("ck_politica_sancion_positiva", type_="check")
        lote.drop_column("max_items_simultaneos")
        lote.drop_column("dias_sancion_por_dia_atraso")

    # RESERVADO deja de ser estado físico. La disponibilidad se deriva por fecha.
    bind.execute(sa.text(
        "UPDATE items SET estado = 'DISPONIBLE' WHERE estado = 'RESERVADO'"))
    with op.batch_alter_table("items") as lote:
        lote.drop_constraint("ck_item_estado_valido", type_="check")
        lote.create_check_constraint(
            "ck_item_estado_valido",
            "estado IN ('DISPONIBLE','PRESTADO','EN_MANTENIMIENTO',"
            "'DADO_DE_BAJA','EXTRAVIADO')")

    with op.batch_alter_table("reservas") as lote:
        lote.drop_constraint("ck_reserva_estado_valido", type_="check")
        lote.create_check_constraint(
            "ck_reserva_estado_valido",
            "estado IN ('PENDIENTE','CONFIRMADA','EXPIRADA','CANCELADA',"
            "'CONVERTIDA','RECHAZADA','RETIRADA')")

    # Las versiones anteriores permitían repetir exactamente una solicitud. Se
    # conserva la confirmada (o la más antigua) y se cierran las copias antes de
    # crear la garantía única. Esto permite migrar bases que ya sufrieron el bug.
    reservas = sa.table(
        "reservas",
        sa.column("id", sa.Integer()),
        sa.column("usuario_id", sa.Integer()),
        sa.column("item_id", sa.Integer()),
        sa.column("fecha_inicio", sa.Date()),
        sa.column("fecha_fin", sa.Date()),
        sa.column("estado", sa.String(20)),
        sa.column("motivo_resolucion", sa.String(300)),
    )
    activas = bind.execute(sa.select(reservas).where(
        reservas.c.estado.in_(("PENDIENTE", "CONFIRMADA"))).order_by(
            sa.case((reservas.c.estado == "CONFIRMADA", 0), else_=1),
            reservas.c.id)).mappings()
    vistas = set()
    for fila in activas:
        clave = (fila["usuario_id"], fila["item_id"],
                 fila["fecha_inicio"], fila["fecha_fin"])
        if clave in vistas:
            bind.execute(reservas.update().where(
                reservas.c.id == fila["id"]).values(
                    estado="RECHAZADA",
                    motivo_resolucion="Solicitud duplicada cerrada durante la migración."))
        else:
            vistas.add(clave)
    op.create_index(
        "ux_reserva_usuario_item_rango_activo", "reservas",
        ["usuario_id", "item_id", "fecha_inicio", "fecha_fin"], unique=True,
        sqlite_where=sa.text("estado IN ('PENDIENTE','CONFIRMADA')"),
        postgresql_where=sa.text("estado IN ('PENDIENTE','CONFIRMADA')"))

    with op.batch_alter_table("prestamos") as lote:
        lote.drop_constraint("ck_prestamo_renovaciones_no_negativas", type_="check")
        lote.drop_constraint("ck_prestamo_aplazamiento_no_negativo", type_="check")
        lote.drop_column("numero_renovaciones")
        lote.drop_column("dias_aplazados")

    op.create_table(
        "eventos_reserva",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reserva_id", sa.Integer(),
                  sa.ForeignKey("reservas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("actor_tipo", sa.String(10), nullable=False),
        sa.Column("actor_usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id")),
        sa.Column("motivo", sa.String(300)),
        sa.Column("fecha_inicio_anterior", sa.Date()),
        sa.Column("fecha_fin_anterior", sa.Date()),
        sa.Column("fecha_inicio_nueva", sa.Date()),
        sa.Column("fecha_fin_nueva", sa.Date()),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "actor_tipo IN ('USUARIO','SISTEMA')", name="ck_evento_reserva_actor_tipo"),
    )
    op.create_index(
        "ix_eventos_reserva_reserva_fecha", "eventos_reserva", ["reserva_id", "creado_en"])

    eventos = sa.table(
        "eventos_reserva",
        sa.column("reserva_id", sa.Integer()),
        sa.column("tipo", sa.String(30)),
        sa.column("actor_tipo", sa.String(10)),
        sa.column("creado_en", sa.DateTime(timezone=True)),
    )
    reservas_existentes = sa.table(
        "reservas",
        sa.column("id", sa.Integer()),
        sa.column("fecha_solicitud", sa.DateTime(timezone=True)),
    )
    bind.execute(eventos.insert().from_select(
        ["reserva_id", "tipo", "actor_tipo", "creado_en"],
        sa.select(
            reservas_existentes.c.id,
            sa.literal("MIGRADA"),
            sa.literal("SISTEMA"),
            reservas_existentes.c.fecha_solicitud,
        )))

    op.create_table(
        "aplazamientos_prestamo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prestamo_id", sa.Integer(),
                  sa.ForeignKey("prestamos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cierre_id", sa.Integer(), sa.ForeignKey("dias_no_laborables.id")),
        sa.Column("fecha_anterior", sa.Date(), nullable=False),
        sa.Column("fecha_nueva", sa.Date(), nullable=False),
        sa.Column("aplicado_en", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_aplazamientos_prestamo_fecha", "aplazamientos_prestamo",
        ["prestamo_id", "aplicado_en"])


def downgrade():
    op.drop_index("ix_aplazamientos_prestamo_fecha", table_name="aplazamientos_prestamo")
    op.drop_table("aplazamientos_prestamo")
    op.drop_index("ix_eventos_reserva_reserva_fecha", table_name="eventos_reserva")
    op.drop_table("eventos_reserva")

    with op.batch_alter_table("prestamos") as lote:
        lote.add_column(sa.Column(
            "numero_renovaciones", sa.Integer(), nullable=False, server_default="0"))
        lote.add_column(sa.Column(
            "dias_aplazados", sa.Integer(), nullable=False, server_default="0"))
        lote.create_check_constraint(
            "ck_prestamo_renovaciones_no_negativas", "numero_renovaciones >= 0")
        lote.create_check_constraint(
            "ck_prestamo_aplazamiento_no_negativo", "dias_aplazados >= 0")

    op.drop_index("ux_reserva_usuario_item_rango_activo", table_name="reservas")
    op.execute(
        "UPDATE reservas SET estado = 'CANCELADA' WHERE estado = 'RETIRADA'")
    with op.batch_alter_table("reservas") as lote:
        lote.drop_constraint("ck_reserva_estado_valido", type_="check")
        lote.create_check_constraint(
            "ck_reserva_estado_valido",
            "estado IN ('PENDIENTE','CONFIRMADA','EXPIRADA','CANCELADA',"
            "'CONVERTIDA','RECHAZADA')")

    with op.batch_alter_table("items") as lote:
        lote.drop_constraint("ck_item_estado_valido", type_="check")
        lote.create_check_constraint(
            "ck_item_estado_valido",
            "estado IN ('DISPONIBLE','PRESTADO','RESERVADO','EN_MANTENIMIENTO',"
            "'DADO_DE_BAJA','EXTRAVIADO')")

    with op.batch_alter_table("politicas_servicio") as lote:
        lote.add_column(sa.Column(
            "max_items_simultaneos", sa.Integer(), nullable=False, server_default="1"))
        lote.add_column(sa.Column(
            "dias_sancion_por_dia_atraso", sa.Integer(), nullable=False, server_default="1"))
        lote.create_check_constraint("ck_politica_max_positivo", "max_items_simultaneos > 0")
        lote.create_check_constraint(
            "ck_politica_sancion_positiva", "dias_sancion_por_dia_atraso > 0")
    op.drop_table("politicas_rol")
