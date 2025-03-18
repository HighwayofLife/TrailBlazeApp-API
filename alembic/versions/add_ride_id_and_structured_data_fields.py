"""Add ride_id and update structured data fields

Revision ID: 9db4a8c2ff53
Revises: f8c14a5c4fa9
Create Date: 2024-03-18 20:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9db4a8c2ff53'
down_revision = 'f8c14a5c4fa9'
branch_labels = None
depends_on = None


def upgrade():
    # Add ride_id column to events table
    op.add_column('events', sa.Column('ride_id', sa.String(), nullable=True))
    
    # Add has_intro_ride column for direct access (not just in event_details)
    op.add_column('events', sa.Column('has_intro_ride', sa.Boolean(), nullable=True, server_default='false'))
    
    # Add comment to event_details column to clarify its purpose
    op.alter_column('events', 'event_details',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               comment='Structured event data including location_details, coordinates, control_judges, and other metadata',
               existing_nullable=True)
    
    # Create an index on ride_id for faster lookups
    op.create_index(op.f('ix_events_ride_id'), 'events', ['ride_id'], unique=False)
    
    # Add comment on distances column to clarify expected format
    op.alter_column('events', 'distances',
               existing_type=postgresql.ARRAY(sa.VARCHAR()),
               comment='List of distances in format "25 miles", "50 miles", etc. Full details in event_details.distances',
               existing_nullable=True)


def downgrade():
    # Remove index
    op.drop_index(op.f('ix_events_ride_id'), table_name='events')
    
    # Remove comments
    op.alter_column('events', 'event_details',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               comment=None,
               existing_nullable=True)
    
    op.alter_column('events', 'distances',
               existing_type=postgresql.ARRAY(sa.VARCHAR()),
               comment=None,
               existing_nullable=True)
    
    # Remove columns
    op.drop_column('events', 'has_intro_ride')
    op.drop_column('events', 'ride_id') 