"""create receipts and communication history tables

Revision ID: 0009_create_receipts_communication_tables
Revises: 0008_create_billing_payment_tables
Create Date: 2026-09-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0009_create_receipts_communication_tables'
down_revision = '0008_create_billing_payment_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create receipts table
    op.create_table(
        'receipts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('shop_id', sa.Integer(), nullable=False),
        sa.Column('billing_id', sa.Integer(), nullable=True),
        sa.Column('payment_id', sa.Integer(), nullable=True),
        sa.Column('receipt_number', sa.String(length=50), nullable=False),
        sa.Column('receipt_type', sa.String(length=20), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('generated_by', sa.Integer(), nullable=False),
        sa.Column('storage_key', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='generated'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['billing_id'], ['billings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['shop_id'], ['shops.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['generated_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_receipts_shop_id'), 'receipts', ['shop_id'], unique=False)
    op.create_index(op.f('ix_receipts_billing_id'), 'receipts', ['billing_id'], unique=False)
    op.create_index(op.f('ix_receipts_payment_id'), 'receipts', ['payment_id'], unique=False)
    op.create_index(op.f('ix_receipts_receipt_number'), 'receipts', ['receipt_number'], unique=True)
    op.create_index(op.f('ix_receipts_receipt_type'), 'receipts', ['receipt_type'], unique=False)
    op.create_index(op.f('ix_receipts_generated_by'), 'receipts', ['generated_by'], unique=False)
    op.create_index(op.f('ix_receipts_status'), 'receipts', ['status'], unique=False)

    # Check constraints for receipts
    op.create_check_constraint(
        'ck_receipt_type',
        'receipts',
        "receipt_type IN ('invoice', 'payment_receipt')",
    )
    op.create_check_constraint(
        'ck_receipt_status',
        'receipts',
        "status IN ('generated', 'sent', 'failed', 'archived')",
    )
    # Ensure at least one of billing_id or payment_id is set
    op.create_check_constraint(
        'ck_receipt_has_reference',
        'receipts',
        '(billing_id IS NOT NULL) != (payment_id IS NOT NULL)',
    )

    # Create communication_history table
    op.create_table(
        'communication_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('shop_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('application_id', sa.Integer(), nullable=True),
        sa.Column('payment_id', sa.Integer(), nullable=True),
        sa.Column('billing_id', sa.Integer(), nullable=True),
        sa.Column('receipt_id', sa.Integer(), nullable=True),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('recipient', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('provider', sa.String(length=50), nullable=True),
        sa.Column('provider_message_id', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['shop_id'], ['shops.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['billing_id'], ['billings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['receipt_id'], ['receipts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_communication_history_shop_id'), 'communication_history', ['shop_id'], unique=False)
    op.create_index(op.f('ix_communication_history_customer_id'), 'communication_history', ['customer_id'], unique=False)
    op.create_index(op.f('ix_communication_history_application_id'), 'communication_history', ['application_id'], unique=False)
    op.create_index(op.f('ix_communication_history_payment_id'), 'communication_history', ['payment_id'], unique=False)
    op.create_index(op.f('ix_communication_history_billing_id'), 'communication_history', ['billing_id'], unique=False)
    op.create_index(op.f('ix_communication_history_receipt_id'), 'communication_history', ['receipt_id'], unique=False)
    op.create_index(op.f('ix_communication_history_channel'), 'communication_history', ['channel'], unique=False)
    op.create_index(op.f('ix_communication_history_status'), 'communication_history', ['status'], unique=False)
    op.create_index(op.f('ix_communication_history_created_at'), 'communication_history', ['created_at'], unique=False)
    # Composite index for duplicate-send protection (same receipt + channel + recipient within short window)
    op.create_index(
        'ix_communication_duplicate_check',
        'communication_history',
        ['receipt_id', 'channel', 'recipient', 'created_at'],
        unique=False
    )

    # Check constraints for communication_history
    op.create_check_constraint(
        'ck_communication_channel',
        'communication_history',
        "channel IN ('email', 'whatsapp', 'sms')",
    )
    op.create_check_constraint(
        'ck_communication_status',
        'communication_history',
        "status IN ('pending', 'queued', 'sent', 'failed', 'cancelled')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_communication_status', 'communication_history', type_='check')
    op.drop_constraint('ck_communication_channel', 'communication_history', type_='check')
    op.drop_index(op.f('ix_communication_duplicate_check'), table_name='communication_history')
    op.drop_index(op.f('ix_communication_history_created_at'), table_name='communication_history')
    op.drop_index(op.f('ix_communication_history_status'), table_name='communication_history')
    op.drop_index(op.f('ix_communication_history_channel'), table_name='communication_history')
    op.drop_index(op.f('ix_communication_history_receipt_id'), table_name='communication_history')
    op.drop_index(op.f('ix_communication_history_billing_id'), table_name='communication_history')
    op.drop_index(op.f('ix_communication_history_payment_id'), table_name='communication_history')
    op.drop_index(op.f('ix_communication_history_application_id'), table_name='communication_history')
    op.drop_index(op.f('ix_communication_history_customer_id'), table_name='communication_history')
    op.drop_index(op.f('ix_communication_history_shop_id'), table_name='communication_history')
    op.drop_table('communication_history')

    op.drop_constraint('ck_receipt_has_reference', 'receipts', type_='check')
    op.drop_constraint('ck_receipt_status', 'receipts', type_='check')
    op.drop_constraint('ck_receipt_type', 'receipts', type_='check')
    op.drop_index(op.f('ix_receipts_status'), table_name='receipts')
    op.drop_index(op.f('ix_receipts_generated_by'), table_name='receipts')
    op.drop_index(op.f('ix_receipts_receipt_type'), table_name='receipts')
    op.drop_index(op.f('ix_receipts_receipt_number'), table_name='receipts')
    op.drop_index(op.f('ix_receipts_payment_id'), table_name='receipts')
    op.drop_index(op.f('ix_receipts_billing_id'), table_name='receipts')
    op.drop_index(op.f('ix_receipts_shop_id'), table_name='receipts')
    op.drop_table('receipts')