"""listing-shaped columns on facilities, units, observations

Revision ID: 002_listing
Revises: 001_initial
Create Date: 2026-08-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_listing"
down_revision: Union[str, Sequence[str], None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "facilities",
        sa.Column(
            "asset_type",
            sa.String(),
            nullable=False,
            server_default="self_storage",
        ),
    )
    op.add_column(
        "facilities",
        sa.Column(
            "attributes",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.add_column("units", sa.Column("square_footage", sa.Integer(), nullable=True))
    op.add_column(
        "units",
        sa.Column(
            "attributes",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "units",
        sa.Column(
            "price_data_available",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.execute(
        """
        UPDATE units
        SET square_footage = width_ft * length_ft,
            attributes = jsonb_build_object(
                'width_ft', width_ft,
                'length_ft', length_ft,
                'features', COALESCE(features, '[]'::jsonb)
            )
        """
    )
    op.alter_column("units", "square_footage", nullable=False)
    op.alter_column("units", "width_ft", existing_type=sa.Integer(), nullable=True)
    op.alter_column("units", "length_ft", existing_type=sa.Integer(), nullable=True)

    op.add_column("observations", sa.Column("price", sa.Integer(), nullable=True))
    op.add_column("observations", sa.Column("price_unit", sa.String(), nullable=True))
    op.add_column(
        "observations",
        sa.Column(
            "price_data_available",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.execute(
        """
        UPDATE observations
        SET price = standard_price,
            price_unit = 'per_unit_per_month',
            price_data_available = true
        """
    )


def downgrade() -> None:
    op.drop_column("observations", "price_data_available")
    op.drop_column("observations", "price_unit")
    op.drop_column("observations", "price")
    op.alter_column("units", "length_ft", existing_type=sa.Integer(), nullable=False)
    op.alter_column("units", "width_ft", existing_type=sa.Integer(), nullable=False)
    op.drop_column("units", "price_data_available")
    op.drop_column("units", "attributes")
    op.drop_column("units", "square_footage")
    op.drop_column("facilities", "attributes")
    op.drop_column("facilities", "asset_type")
