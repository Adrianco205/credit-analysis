"""Persist canonical snapshot and projection validation result.

Revision ID: 20260715001
Revises: 20260307001
Create Date: 2026-07-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260715001"
down_revision: Union[str, None] = "20260307001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("analisis_hipotecario", sa.Column("normalized_snapshot_json", sa.JSON(), nullable=True))
    op.add_column("analisis_hipotecario", sa.Column("projection_validation_status", sa.String(40), nullable=True))
    op.add_column("analisis_hipotecario", sa.Column("manual_overrides_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("analisis_hipotecario", "projection_validation_status")
    op.drop_column("analisis_hipotecario", "manual_overrides_json")
    op.drop_column("analisis_hipotecario", "normalized_snapshot_json")
