"""Add projected cost fields to propuestas_ahorro

Revision ID: 20260307001
Revises: 20260208001
Create Date: 2026-03-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260307001"
down_revision: Union[str, None] = "20260208001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "propuestas_ahorro",
        sa.Column("costo_total_proyectado", sa.Numeric(15, 2), nullable=True),
    )
    op.add_column(
        "propuestas_ahorro",
        sa.Column("costo_total_proyectado_banco", sa.Numeric(15, 2), nullable=True),
    )
    op.add_column(
        "propuestas_ahorro",
        sa.Column("total_subsidio_frech_proyectado", sa.Numeric(15, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("propuestas_ahorro", "total_subsidio_frech_proyectado")
    op.drop_column("propuestas_ahorro", "costo_total_proyectado_banco")
    op.drop_column("propuestas_ahorro", "costo_total_proyectado")
