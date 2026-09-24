"""Add platform_manager_shops table for Platform Manager shop assignments.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-21

Adds: platform_manager_shops table linking Platform Managers to shops.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platform_manager_shops",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("shop_id", sa.BigInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.sql.expression.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "shop_id", name="uq_manager_shop_assignment"),
    )
    op.create_index("ix_platform_manager_shops_user_id", "platform_manager_shops", ["user_id"])
    op.create_index("ix_platform_manager_shops_shop_id", "platform_manager_shops", ["shop_id"])


def downgrade() -> None:
    op.drop_index("ix_platform_manager_shops_shop_id", table_name="platform_manager_shops")
    op.drop_index("ix_platform_manager_shops_user_id", table_name="platform_manager_shops")
    op.drop_table("platform_manager_shops")