"""
TEMPLATE: Add pgvector support and embeddings tables

This is a TEMPLATE showing what your Alembic migration should contain.
After running 'alembic revision --autogenerate', you'll need to manually
add the pgvector extension creation and index creation.

Revision ID: XXXXX
Revises: YYYYY
Create Date: 2026-01-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = 'XXXXX'  # Will be auto-generated
down_revision = 'YYYYY'  # Will be auto-generated
branch_labels = None
depends_on = None


def upgrade():
    # 1. Enable pgvector extension (MUST BE FIRST)
    op.execute('CREATE EXTENSION IF NOT EXISTS vector;')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    
    # 2. Create documents table
    op.create_table('documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=True),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.session_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_session_id'), 'documents', ['session_id'], unique=False)
    
    # 3. Create chunks table
    op.create_table('chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.session_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chunks_document_id'), 'chunks', ['document_id'], unique=False)
    op.create_index(op.f('ix_chunks_session_id'), 'chunks', ['session_id'], unique=False)
    
    # 4. Create embeddings table with vector column
    op.create_table('embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=False),  # pgvector column
        sa.Column('embedding_model', sa.String(length=100), nullable=True),
        sa.Column('text_preview', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['chunk_id'], ['chunks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.session_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_embeddings_chunk_id'), 'embeddings', ['chunk_id'], unique=False)
    op.create_index(op.f('ix_embeddings_document_id'), 'embeddings', ['document_id'], unique=False)
    op.create_index(op.f('ix_embeddings_session_id'), 'embeddings', ['session_id'], unique=False)
    
    # 5. Create vector similarity index (IVFFLAT for faster searches)
    # Note: This is critical for performance!
    op.execute('''
        CREATE INDEX idx_embeddings_vector_ivfflat 
        ON embeddings 
        USING ivfflat (embedding vector_cosine_ops) 
        WITH (lists = 100);
    ''')
    
    # Alternative: Use HNSW index (PostgreSQL 14+, faster but uses more memory)
    # op.execute('''
    #     CREATE INDEX idx_embeddings_vector_hnsw 
    #     ON embeddings 
    #     USING hnsw (embedding vector_cosine_ops);
    # ''')


def downgrade():
    # Drop in reverse order
    op.execute('DROP INDEX IF EXISTS idx_embeddings_vector_ivfflat;')
    # op.execute('DROP INDEX IF EXISTS idx_embeddings_vector_hnsw;')
    
    op.drop_index(op.f('ix_embeddings_session_id'), table_name='embeddings')
    op.drop_index(op.f('ix_embeddings_document_id'), table_name='embeddings')
    op.drop_index(op.f('ix_embeddings_chunk_id'), table_name='embeddings')
    op.drop_table('embeddings')
    
    op.drop_index(op.f('ix_chunks_session_id'), table_name='chunks')
    op.drop_index(op.f('ix_chunks_document_id'), table_name='chunks')
    op.drop_table('chunks')
    
    op.drop_index(op.f('ix_documents_session_id'), table_name='documents')
    op.drop_table('documents')
    
    # Note: Don't drop extensions as other databases might use them
    # op.execute('DROP EXTENSION IF EXISTS vector;')
