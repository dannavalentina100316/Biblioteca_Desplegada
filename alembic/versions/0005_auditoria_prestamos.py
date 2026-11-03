"""Registra al usuario que creó cada préstamo.

Revision ID: 0005_auditoria_prestamos
Revises: 0004_refresh_tokens
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_auditoria_prestamos"
down_revision = "0004_refresh_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("prestamos") as batch_op:
        batch_op.add_column(
            sa.Column("registrado_por_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_prestamos_registrado_por_id_usuarios",
            "usuarios",
            ["registrado_por_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("prestamos") as batch_op:
        batch_op.drop_constraint(
            "fk_prestamos_registrado_por_id_usuarios",
            type_="foreignkey",
        )
        batch_op.drop_column("registrado_por_id")
