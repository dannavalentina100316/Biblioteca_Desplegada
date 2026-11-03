"""Crea usuarios y roles.

Revision ID: 0003_usuarios
Revises: 0002_multa_pagada
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_usuarios"
down_revision = "0002_multa_pagada"
branch_labels = None
depends_on = None

rolusuario = sa.Enum("admin", "bibliotecario", "socio", name="rolusuario")


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("rol", rolusuario, nullable=False),
        sa.Column(
            "activo",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "intentos_fallidos",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("bloqueado_hasta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("socio_id", sa.Integer(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["socio_id"],
            ["socios.id"],
            name="fk_usuarios_socio_id_socios",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_usuarios"),
        sa.UniqueConstraint("socio_id", name="uq_usuarios_socio_id"),
    )
    op.create_index("ix_usuarios_id", "usuarios", ["id"], unique=False)
    op.create_index("ix_usuarios_email", "usuarios", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_usuarios_email", table_name="usuarios")
    op.drop_index("ix_usuarios_id", table_name="usuarios")
    op.drop_table("usuarios")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="rolusuario").drop(bind, checkfirst=True)
