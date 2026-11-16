"""Agregar reportes ciudadanos.

Revision ID: 8d4a0f1c6b72
Revises: f16109da523b
Create Date: 2026-11-15 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "8d4a0f1c6b72"
down_revision = "f16109da523b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reportes_ciudadanos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("municipio", sa.String(length=100), nullable=False),
        sa.Column("barrio", sa.String(length=120), nullable=False),
        sa.Column("tipo_falla", sa.String(length=40), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("reportes_ciudadanos", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_reportes_ciudadanos_creado_en"), ["creado_en"], unique=False)


def downgrade():
    with op.batch_alter_table("reportes_ciudadanos", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_reportes_ciudadanos_creado_en"))
    op.drop_table("reportes_ciudadanos")
