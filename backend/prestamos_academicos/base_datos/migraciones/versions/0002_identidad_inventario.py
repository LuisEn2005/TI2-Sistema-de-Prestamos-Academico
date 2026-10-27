"""Sprint 2: identidad (credenciales, perfiles, políticas) e inventario ampliado.

- usuarios: correo, contraseña, estado activo y caché de sanción.
- perfiles por rol y políticas de servicio.
- recursos -> items: estado completo, categoría, atributos por tipo y texto de búsqueda.
- prestamos.recurso_id -> item_id.

Los usuarios heredados del MVP reciben el perfil ESTUDIANTE (código HEREDADO-<id>) y
quedan sin contraseña: un gestor debe revisarlos y asignarles acceso.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # ---- usuarios -------------------------------------------------------
    with op.batch_alter_table("usuarios") as lote:
        lote.add_column(sa.Column("correo", sa.String(160), nullable=True))
        lote.add_column(sa.Column("password_hash", sa.String(255), nullable=True))
        lote.add_column(sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.true()))
        lote.add_column(sa.Column("tiene_sancion_activa_cache", sa.Boolean, nullable=False,
                                  server_default=sa.false()))
        lote.add_column(sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False,
                                  server_default=sa.func.now()))
    ids = [fila[0] for fila in bind.execute(sa.text("SELECT id FROM usuarios"))]
    for uid in ids:
        bind.execute(
            sa.text("UPDATE usuarios SET correo = :c WHERE id = :i"),
            {"c": f"usuario{uid}@sin-correo.local", "i": uid},
        )
    with op.batch_alter_table("usuarios") as lote:
        lote.alter_column("correo", existing_type=sa.String(160), nullable=False)
        lote.create_unique_constraint("uq_usuarios_correo", ["correo"])

    # ---- políticas y perfiles ------------------------------------------
    op.create_table(
        "politicas_servicio",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("rol_aplicable", sa.String(30), nullable=False, unique=True),
        sa.Column("max_items_simultaneos", sa.Integer, nullable=False),
        sa.Column("dias_prestamo_default", sa.Integer, nullable=False),
        sa.Column("dias_gracia_reserva", sa.Integer, nullable=False),
        sa.Column("tipos_recurso_permitidos", sa.String(200), nullable=False),
    )
    usuario_fk = lambda: sa.Column(  # noqa: E731
        "usuario_id", sa.Integer, sa.ForeignKey("usuarios.id", ondelete="CASCADE"),
        primary_key=True)
    politica_fk = lambda: sa.Column(  # noqa: E731
        "politica_servicio_id", sa.Integer, sa.ForeignKey("politicas_servicio.id"))
    op.create_table(
        "perfiles_estudiante", usuario_fk(),
        sa.Column("codigo_estudiante", sa.String(30), nullable=False, unique=True),
        sa.Column("matricula_vigente", sa.Boolean, nullable=False, server_default=sa.true()),
        politica_fk(),
    )
    op.create_table(
        "perfiles_docente", usuario_fk(),
        sa.Column("codigo_empleado", sa.String(30), nullable=False, unique=True),
        sa.Column("tipo_contrato", sa.String(60), nullable=False),
        politica_fk(),
    )
    op.create_table(
        "perfiles_administrativo", usuario_fk(),
        sa.Column("codigo_empleado", sa.String(30), nullable=False, unique=True),
        sa.Column("cargo_administrativo", sa.String(80), nullable=False),
        politica_fk(),
    )
    op.create_table(
        "perfiles_gestor_inventario", usuario_fk(),
        sa.Column("codigo_empleado", sa.String(30), nullable=False, unique=True),
        sa.Column("area_responsable", sa.String(80), nullable=False),
        sa.Column("fecha_asignacion", sa.Date, nullable=False),
    )
    for uid in ids:
        bind.execute(
            sa.text("INSERT INTO perfiles_estudiante (usuario_id, codigo_estudiante, "
                    "matricula_vigente) VALUES (:i, :c, :m)"),
            {"i": uid, "c": f"HEREDADO-{uid}", "m": True},
        )

    # ---- recursos -> items ---------------------------------------------
    op.rename_table("recursos", "items")
    with op.batch_alter_table("items") as lote:
        lote.add_column(sa.Column("estado", sa.String(30), nullable=False,
                                  server_default="DISPONIBLE"))
        lote.add_column(sa.Column("categoria", sa.String(80), nullable=True))
        lote.add_column(sa.Column("atributos", sa.JSON, nullable=True))
        lote.add_column(sa.Column("texto_busqueda", sa.Text, nullable=True))
        lote.add_column(sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False,
                                  server_default=sa.func.now()))
        lote.add_column(sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False,
                                  server_default=sa.func.now()))
    op.execute("UPDATE items SET estado = CASE WHEN disponible THEN 'DISPONIBLE' "
               "ELSE 'PRESTADO' END")
    op.execute("UPDATE items SET categoria = tipo")
    op.execute("UPDATE items SET tipo = UPPER(tipo)")
    op.execute("UPDATE items SET atributos = '{}'")
    op.execute("UPDATE items SET texto_busqueda = LOWER(codigo || ' ' || nombre || ' ' || tipo)")
    with op.batch_alter_table("items") as lote:
        lote.drop_column("disponible")
        lote.alter_column("nombre", existing_type=sa.String(120), type_=sa.String(160),
                          existing_nullable=False)
        lote.alter_column("categoria", existing_type=sa.String(80), nullable=False)
        lote.alter_column("atributos", existing_type=sa.JSON, nullable=False)
        lote.alter_column("texto_busqueda", existing_type=sa.Text, nullable=False)
        lote.create_index("ix_items_tipo_estado", ["tipo", "estado"])
        lote.create_index("ix_items_categoria", ["categoria"])

    # ---- prestamos ------------------------------------------------------
    with op.batch_alter_table("prestamos") as lote:
        lote.alter_column("recurso_id", new_column_name="item_id",
                          existing_type=sa.Integer, existing_nullable=False)


def downgrade():
    raise NotImplementedError(
        "La migración 0002 transforma datos del MVP y no se revierte automáticamente."
    )
