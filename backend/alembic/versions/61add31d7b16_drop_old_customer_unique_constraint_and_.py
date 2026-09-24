"""drop_old_customer_unique_constraint_and_add_partial

Revision ID: 61add31d7b16
Revises: 0006_create_application_table
Create Date: 2026-09-22 17:35:08.737061

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61add31d7b16'
down_revision: Union[str, None] = '0006_create_application_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old unique constraint (it is a constraint, not just an index)
    op.drop_constraint('uq_customers_shop_id_mobile', 'customers', type_='unique')
    # Create the partial unique index for non-archived customers
    op.execute(
        "CREATE UNIQUE INDEX uq_customers_shop_id_mobile_active ON customers (shop_id, mobile) WHERE status != 'archived'"
    )


def downgrade() -> None:
    # Drop the partial unique index
    op.execute("DROP INDEX IF EXISTS uq_customers_shop_id_mobile_active")
    # Recreate the old unique constraint
    op.create_unique_constraint('uq_customers_shop_id_mobile', 'customers', ['shop_id', 'mobile'])