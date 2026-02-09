"""Add period components fields to analisis_hipotecario

Revision ID: 20260208001
Revises: 
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260208001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new columns for period components extraction."""
    # Add capital_pagado_periodo
    op.add_column(
        'analisis_hipotecario',
        sa.Column('capital_pagado_periodo', sa.Numeric(15, 2), nullable=True)
    )
    
    # Add intereses_corrientes_periodo
    op.add_column(
        'analisis_hipotecario',
        sa.Column('intereses_corrientes_periodo', sa.Numeric(15, 2), nullable=True)
    )
    
    # Add intereses_mora
    op.add_column(
        'analisis_hipotecario',
        sa.Column('intereses_mora', sa.Numeric(15, 2), nullable=True)
    )
    
    # Add otros_cargos
    op.add_column(
        'analisis_hipotecario',
        sa.Column('otros_cargos', sa.Numeric(15, 2), nullable=True)
    )


def downgrade() -> None:
    """Remove period components columns."""
    op.drop_column('analisis_hipotecario', 'otros_cargos')
    op.drop_column('analisis_hipotecario', 'intereses_mora')
    op.drop_column('analisis_hipotecario', 'intereses_corrientes_periodo')
    op.drop_column('analisis_hipotecario', 'capital_pagado_periodo')
