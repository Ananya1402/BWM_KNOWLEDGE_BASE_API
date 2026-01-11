"""changed IDs to UUID format

Revision ID: 96c6ad85e6be
Revises: cf50b784129b
Create Date: 2026-01-04 19:36:31.699206

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '96c6ad85e6be'
down_revision: Union[str, None] = 'cf50b784129b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the foreign key constraint first (without assuming the name)
    op.execute("""
        ALTER TABLE chat_messages 
        DROP CONSTRAINT IF EXISTS chat_messages_session_id_fkey;
    """)
    
    # Drop indexes if they exist
    op.execute("DROP INDEX IF EXISTS ix_chat_messages_session_id;")
    op.execute("DROP INDEX IF EXISTS ix_chat_sessions_session_id;")
    
    # Drop unique constraint if it exists
    op.execute("""
        ALTER TABLE chat_sessions 
        DROP CONSTRAINT IF EXISTS chat_sessions_session_id_key;
    """)
    
    # Create new UUID columns
    op.add_column('chat_sessions', sa.Column('id_new', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False))
    op.add_column('chat_sessions', sa.Column('session_id_new', postgresql.UUID(as_uuid=True), nullable=False))
    
    op.add_column('chat_messages', sa.Column('id_new', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False))
    op.add_column('chat_messages', sa.Column('session_id_new', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Create session_id mapping: one UUID per unique old session_id
    op.execute("""
        WITH RECURSIVE session_mapping AS (
            SELECT DISTINCT session_id, gen_random_uuid() as new_session_id 
            FROM chat_sessions
        )
        UPDATE chat_sessions cs
        SET session_id_new = sm.new_session_id
        FROM (
            SELECT DISTINCT session_id, gen_random_uuid() as new_session_id 
            FROM chat_sessions
        ) sm
        WHERE cs.session_id = sm.session_id;
    """)
    
    # Update chat_messages session_id_new with mapped UUIDs
    op.execute("""
        UPDATE chat_messages cm
        SET session_id_new = cs.session_id_new
        FROM chat_sessions cs
        WHERE cm.session_id = cs.session_id;
    """)
    
    # Drop old columns
    op.drop_column('chat_sessions', 'id')
    op.drop_column('chat_sessions', 'session_id')
    op.drop_column('chat_messages', 'id')
    op.drop_column('chat_messages', 'session_id')
    
    # Rename new columns to original names
    op.alter_column('chat_sessions', 'id_new', new_column_name='id')
    op.alter_column('chat_sessions', 'session_id_new', new_column_name='session_id')
    op.alter_column('chat_messages', 'id_new', new_column_name='id')
    op.alter_column('chat_messages', 'session_id_new', new_column_name='session_id')
    
    # Recreate primary keys
    op.create_primary_key('chat_sessions_pkey', 'chat_sessions', ['id'])
    op.create_primary_key('chat_messages_pkey', 'chat_messages', ['id'])
    
    # Recreate unique constraint and indexes
    op.create_unique_constraint('chat_sessions_session_id_key', 'chat_sessions', ['session_id'])
    op.create_index('ix_chat_sessions_session_id', 'chat_sessions', ['session_id'])
    op.create_index('ix_chat_messages_session_id', 'chat_messages', ['session_id'])
    
    # Recreate foreign key
    op.create_foreign_key('chat_messages_session_id_fkey', 'chat_messages', 'chat_sessions', 
                         ['session_id'], ['session_id'], ondelete='CASCADE')


def downgrade() -> None:
    # Drop the foreign key constraint
    op.execute("""
        ALTER TABLE chat_messages 
        DROP CONSTRAINT IF EXISTS chat_messages_session_id_fkey;
    """)
    
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_chat_messages_session_id;")
    op.execute("DROP INDEX IF EXISTS ix_chat_sessions_session_id;")
    
    # Drop unique constraint
    op.execute("""
        ALTER TABLE chat_sessions 
        DROP CONSTRAINT IF EXISTS chat_sessions_session_id_key;
    """)
    
    # Create old integer columns
    op.add_column('chat_sessions', sa.Column('id_old', sa.Integer(), autoincrement=True, nullable=False))
    op.add_column('chat_sessions', sa.Column('session_id_old', sa.String(100), nullable=False))
    op.add_column('chat_messages', sa.Column('id_old', sa.Integer(), autoincrement=True, nullable=False))
    op.add_column('chat_messages', sa.Column('session_id_old', sa.String(100), nullable=False))
    
    # We can't convert UUIDs back to integers, so use placeholder values
    op.execute("UPDATE chat_sessions SET session_id_old = 'downgrade-not-supported'")
    op.execute("UPDATE chat_messages SET session_id_old = 'downgrade-not-supported'")
    
    # Drop UUID columns
    op.drop_column('chat_sessions', 'id')
    op.drop_column('chat_sessions', 'session_id')
    op.drop_column('chat_messages', 'id')
    op.drop_column('chat_messages', 'session_id')
    
    # Rename old columns back
    op.alter_column('chat_sessions', 'id_old', new_column_name='id')
    op.alter_column('chat_sessions', 'session_id_old', new_column_name='session_id')
    op.alter_column('chat_messages', 'id_old', new_column_name='id')
    op.alter_column('chat_messages', 'session_id_old', new_column_name='session_id')
    
    # Recreate primary keys
    op.create_primary_key('chat_sessions_pkey', 'chat_sessions', ['id'])
    op.create_primary_key('chat_messages_pkey', 'chat_messages', ['id'])
    
    # Recreate unique constraint and indexes
    op.create_unique_constraint('chat_sessions_session_id_key', 'chat_sessions', ['session_id'])
    op.create_index('ix_chat_sessions_session_id', 'chat_sessions', ['session_id'])
    op.create_index('ix_chat_messages_session_id', 'chat_messages', ['session_id'])
    
    # Recreate foreign key
    op.create_foreign_key('chat_messages_session_id_fkey', 'chat_messages', 'chat_sessions', 
                         ['session_id'], ['session_id'], ondelete='CASCADE')