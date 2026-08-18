"""initial facilities, units, observations

Revision ID: 001_initial
Revises:
Create Date: 2026-08-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "facilities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("provider", "slug", name="uq_facilities_provider_slug"),
        sa.UniqueConstraint("url", name="uq_facilities_url"),
    )
    op.create_table(
        "units",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "facility_id",
            sa.Integer(),
            sa.ForeignKey("facilities.id"),
            nullable=False,
        ),
        sa.Column("identity_key", sa.String(), nullable=False),
        sa.Column("provider_unit_id", sa.String(), nullable=True),
        sa.Column("width_ft", sa.Integer(), nullable=False),
        sa.Column("length_ft", sa.Integer(), nullable=False),
        sa.Column("features", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint(
            "facility_id", "identity_key", name="uq_units_facility_identity"
        ),
    )
    op.create_index("ix_units_facility_id", "units", ["facility_id"])
    op.create_table(
        "observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "unit_id",
            sa.Integer(),
            sa.ForeignKey("units.id"),
            nullable=False,
        ),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("standard_price", sa.Integer(), nullable=True),
        sa.Column("promo_price", sa.Integer(), nullable=True),
        sa.Column("availability_status", sa.String(), nullable=False),
        sa.Column("availability_text", sa.String(), nullable=True),
        sa.Column("free_first_month", sa.Boolean(), nullable=False),
        sa.Column("parse_strategy", sa.String(), nullable=True),
    )
    op.create_index("ix_observations_unit_id", "observations", ["unit_id"])


def downgrade() -> None:
    op.drop_index("ix_observations_unit_id", table_name="observations")
    op.drop_table("observations")
    op.drop_index("ix_units_facility_id", table_name="units")
    op.drop_table("units")
    op.drop_table("facilities")
