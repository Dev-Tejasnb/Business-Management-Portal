"""Add partial unique index for single active shop owner per shop.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-22

Ensures exactly one active SHOP_OWNER per shop via partial unique index.
Also demotes any existing extra active owners to SHOP_MANAGER.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sequence for concurrency-safe shop code generation
    op.execute("CREATE SEQUENCE IF NOT EXISTS shop_code_seq START 1")

    # First, handle existing data: demote extra active owners to SHOP_MANAGER
    # Keep the oldest active owner per shop, demote the rest
    op.execute(
        """
        WITH ranked_owners AS (
            SELECT
                id,
                shop_id,
                ROW_NUMBER() OVER (PARTITION BY shop_id ORDER BY created_at ASC) as rn
            FROM shop_memberships
            WHERE role = 'shop_owner' AND is_active = true
        )
        UPDATE shop_memberships sm
        SET role = 'shop_manager'
        FROM ranked_owners ro
        WHERE sm.id = ro.id
        AND ro.rn > 1;
        """
    )

    # Create partial unique index: one active owner per shop
    op.create_index(
        "ix_shop_memberships_unique_active_owner",
        "shop_memberships",
        ["shop_id"],
        unique=True,
        postgresql_where=sa.text("role = 'shop_owner' AND is_active = true"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_shop_memberships_unique_active_owner",
        table_name="shop_memberships",
        postgresql_where=sa.text("role = 'shop_owner' AND is_active = true"),
    )
    op.execute("DROP SEQUENCE IF EXISTS shop_code_seq")