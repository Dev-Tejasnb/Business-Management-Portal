"""create document table

Revision ID: 0007_create_document_table
Revises: 61add31d7b16
Create Date: 2026-09-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0007_create_document_table'
down_revision = '61add31d7b16'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('shop_id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=False),
        sa.Column('required_document_id', sa.Integer(), nullable=True),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('storage_key', sa.String(length=500), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='uploaded'),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['required_document_id'], ['service_required_documents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['shop_id'], ['shops.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_documents_application_id'), 'documents', ['application_id'], unique=False)
    op.create_index(op.f('ix_documents_required_document_id'), 'documents', ['required_document_id'], unique=False)
    op.create_index(op.f('ix_documents_shop_id'), 'documents', ['shop_id'], unique=False)
    op.create_index(op.f('ix_documents_status'), 'documents', ['status'], unique=False)
    op.create_index(op.f('ix_documents_storage_key'), 'documents', ['storage_key'], unique=True)
    op.create_index(op.f('ix_documents_uploaded_by'), 'documents', ['uploaded_by'], unique=False)
    op.create_index(op.f('ix_documents_verified_by'), 'documents', ['verified_by'], unique=False)

    # Check constraint for status
    op.create_check_constraint(
        'ck_document_status',
        'documents',
        "status IN ('uploaded', 'verified', 'rejected', 'archived')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_document_status', 'documents', type_='check')
    op.drop_index(op.f('ix_documents_verified_by'), table_name='documents')
    op.drop_index(op.f('ix_documents_uploaded_by'), table_name='documents')
    op.drop_index(op.f('ix_documents_storage_key'), table_name='documents')
    op.drop_index(op.f('ix_documents_status'), table_name='documents')
    op.drop_index(op.f('ix_documents_shop_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_required_document_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_application_id'), table_name='documents')
    op.drop_table('documents')
