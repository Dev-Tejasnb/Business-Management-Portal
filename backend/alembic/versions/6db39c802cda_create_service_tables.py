"""Create service management tables

Revision ID: 6db39c802cda
Revises: 0003
Create Date: 2026-09-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6db39c802cda'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create service_categories table
    op.create_table(
        'service_categories',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('name', name='uq_service_categories_name'),
        sa.UniqueConstraint('slug', name='uq_service_categories_slug'),
    )
    op.create_index('ix_service_categories_slug', 'service_categories', ['slug'], unique=True)

    # Create services table
    op.create_table(
        'services',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column('shop_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('base_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('estimated_processing_days', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['service_categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['shop_id'], ['shops.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_services_shop_id', 'services', ['shop_id'])
    op.create_index('ix_services_category_id', 'services', ['category_id'])
    op.create_index('ix_services_status', 'services', ['status'])
    # Unique slug per shop
    op.create_unique_constraint('uq_services_shop_slug', 'services', ['shop_id', 'slug'])

    # Create service_required_documents table
    op.create_table(
        'service_required_documents',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column('service_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_mandatory', sa.Boolean(), nullable=False, default=True),
        sa.Column('allowed_file_types', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('max_file_size_mb', sa.Integer(), nullable=True, default=10),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_service_required_documents_service_id', 'service_required_documents', ['service_id'])

    # Create service_fields table
    op.create_table(
        'service_fields',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column('service_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('field_type', sa.String(length=50), nullable=False, default='text'),
        sa.Column('is_required', sa.Boolean(), nullable=False, default=False),
        sa.Column('options', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('validation_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_service_fields_service_id', 'service_fields', ['service_id'])


def downgrade() -> None:
    op.drop_index('ix_service_fields_service_id', table_name='service_fields')
    op.drop_table('service_fields')
    op.drop_index('ix_service_required_documents_service_id', table_name='service_required_documents')
    op.drop_table('service_required_documents')
    op.drop_constraint('uq_services_shop_slug', 'services', type_='unique')
    op.drop_index('ix_services_status', table_name='services')
    op.drop_index('ix_services_category_id', table_name='services')
    op.drop_index('ix_services_shop_id', table_name='services')
    op.drop_table('services')
    op.drop_index('ix_service_categories_slug', table_name='service_categories')
    op.drop_table('service_categories')