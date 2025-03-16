"""add event status columns
Revision ID: add_event_status_columns
Revises: d8b45f9a2e55
Create Date: 2024-03-15 22:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_event_status_columns'
down_revision = 'd8b45f9a2e55'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add is_canceled and is_verified columns with default values
    op.add_column('events', sa.Column('is_canceled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('events', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'))
    
    # Create indexes for efficient filtering
    op.create_index('ix_events_is_canceled', 'events', ['is_canceled'], unique=False)
    op.create_index('ix_events_is_verified', 'events', ['is_verified'], unique=False)

def downgrade() -> None:
    # Remove indexes first
    op.drop_index('ix_events_is_canceled', table_name='events')
    op.drop_index('ix_events_is_verified', table_name='events')
    
    # Remove columns
    op.drop_column('events', 'is_canceled')
    op.drop_column('events', 'is_verified')