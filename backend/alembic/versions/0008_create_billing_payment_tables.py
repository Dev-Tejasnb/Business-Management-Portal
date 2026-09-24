"""create billing and payment tables

Revision ID: 0008_create_billing_payment_tables
Revises: 0007_create_document_table
Create Date: 2026-09-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0008_create_billing_payment_tables'
down_revision = '0007_create_document_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create billings table
    op.create_table(
        'billings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('shop_id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('invoice_number', sa.String(length=50), nullable=False),
        sa.Column('service_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('non_service_charges', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('subtotal', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('discount_type', sa.String(length=20), nullable=True),
        sa.Column('discount_value', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('discount_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('discount_reason', sa.Text(), nullable=True),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('amount_paid', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('balance_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('payment_status', sa.String(length=20), nullable=False, server_default='unpaid'),
        sa.Column('billing_status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['shop_id'], ['shops.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_billings_application_id'), 'billings', ['application_id'], unique=False)
    op.create_index(op.f('ix_billings_customer_id'), 'billings', ['customer_id'], unique=False)
    op.create_index(op.f('ix_billings_invoice_number'), 'billings', ['invoice_number'], unique=True)
    op.create_index(op.f('ix_billings_payment_status'), 'billings', ['payment_status'], unique=False)
    op.create_index(op.f('ix_billings_shop_id'), 'billings', ['shop_id'], unique=False)
    op.create_index(op.f('ix_billings_billing_status'), 'billings', ['billing_status'], unique=False)

    # Check constraints for billings
    op.create_check_constraint(
        'ck_billing_service_amount_nonneg',
        'billings',
        'service_amount >= 0',
    )
    op.create_check_constraint(
        'ck_billing_non_service_charges_nonneg',
        'billings',
        'non_service_charges >= 0',
    )
    op.create_check_constraint(
        'ck_billing_discount_amount_nonneg',
        'billings',
        'discount_amount >= 0',
    )
    op.create_check_constraint(
        'ck_billing_total_amount_nonneg',
        'billings',
        'total_amount >= 0',
    )
    op.create_check_constraint(
        'ck_billing_amount_paid_nonneg',
        'billings',
        'amount_paid >= 0',
    )
    op.create_check_constraint(
        'ck_billing_balance_amount_nonneg',
        'billings',
        'balance_amount >= 0',
    )
    op.create_check_constraint(
        'ck_billing_paid_not_exceed_total',
        'billings',
        'amount_paid <= total_amount',
    )
    op.create_check_constraint(
        'ck_billing_status',
        'billings',
        "billing_status IN ('draft', 'issued', 'void')",
    )
    op.create_check_constraint(
        'ck_payment_status',
        'billings',
        "payment_status IN ('unpaid', 'partially_paid', 'paid')",
    )

    # Create billing_items table
    op.create_table(
        'billing_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('billing_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('is_service_item', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('service_id', sa.Integer(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['billing_id'], ['billings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_billing_items_billing_id'), 'billing_items', ['billing_id'], unique=False)
    op.create_index(op.f('ix_billing_items_service_id'), 'billing_items', ['service_id'], unique=False)

    op.create_check_constraint(
        'ck_billing_item_amount_nonneg',
        'billing_items',
        'amount >= 0',
    )

    # Create payments table
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('shop_id', sa.Integer(), nullable=False),
        sa.Column('billing_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('payment_method', sa.String(length=30), nullable=False),
        sa.Column('reference_number', sa.String(length=255), nullable=True),
        sa.Column('reference_exception', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('reference_exception_reason', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('recorded_by', sa.Integer(), nullable=False),
        sa.Column('paid_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['billing_id'], ['billings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['shop_id'], ['shops.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recorded_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_payments_billing_id'), 'payments', ['billing_id'], unique=False)
    op.create_index(op.f('ix_payments_reference_number'), 'payments', ['reference_number'], unique=False)
    op.create_index(op.f('ix_payments_shop_id'), 'payments', ['shop_id'], unique=False)
    op.create_index(op.f('ix_payments_paid_at'), 'payments', ['paid_at'], unique=False)

    op.create_check_constraint(
        'ck_payment_amount_positive',
        'payments',
        'amount > 0',
    )
    op.create_check_constraint(
        'ck_payment_method',
        'payments',
        "payment_method IN ('cash', 'upi', 'card', 'bank_transfer', 'other')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_payment_method', 'payments', type_='check')
    op.drop_constraint('ck_payment_amount_positive', 'payments', type_='check')
    op.drop_index(op.f('ix_payments_paid_at'), table_name='payments')
    op.drop_index(op.f('ix_payments_shop_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_reference_number'), table_name='payments')
    op.drop_index(op.f('ix_payments_billing_id'), table_name='payments')
    op.drop_table('payments')

    op.drop_constraint('ck_billing_item_amount_nonneg', 'billing_items', type_='check')
    op.drop_index(op.f('ix_billing_items_service_id'), table_name='billing_items')
    op.drop_index(op.f('ix_billing_items_billing_id'), table_name='billing_items')
    op.drop_table('billing_items')

    op.drop_constraint('ck_payment_status', 'billings', type_='check')
    op.drop_constraint('ck_billing_status', 'billings', type_='check')
    op.drop_constraint('ck_billing_paid_not_exceed_total', 'billings', type_='check')
    op.drop_constraint('ck_billing_balance_amount_nonneg', 'billings', type_='check')
    op.drop_constraint('ck_billing_amount_paid_nonneg', 'billings', type_='check')
    op.drop_constraint('ck_billing_total_amount_nonneg', 'billings', type_='check')
    op.drop_constraint('ck_billing_discount_amount_nonneg', 'billings', type_='check')
    op.drop_constraint('ck_billing_non_service_charges_nonneg', 'billings', type_='check')
    op.drop_constraint('ck_billing_service_amount_nonneg', 'billings', type_='check')
    op.drop_index(op.f('ix_billings_billing_status'), table_name='billings')
    op.drop_index(op.f('ix_billings_shop_id'), table_name='billings')
    op.drop_index(op.f('ix_billings_payment_status'), table_name='billings')
    op.drop_index(op.f('ix_billings_invoice_number'), table_name='billings')
    op.drop_index(op.f('ix_billings_customer_id'), table_name='billings')
    op.drop_index(op.f('ix_billings_application_id'), table_name='billings')
    op.drop_table('billings')