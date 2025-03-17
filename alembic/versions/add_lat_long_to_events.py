"""Add latitude and longitude to events table

Revision ID: add_lat_long_to_events
Revises: 3dc01b60beeb
Create Date: 2025-03-17 21:25:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'add_lat_long_to_events'
down_revision = '3dc01b60beeb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if the events table exists
    conn = op.get_bind()
    inspector = inspect(conn)
    if "events" not in inspector.get_table_names():
        # Create the events table if it doesn't exist
        op.create_table(
            'events',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('location', sa.String(255), nullable=False),
            sa.Column('date_start', sa.DateTime(), nullable=False),
            sa.Column('date_end', sa.DateTime(), nullable=True),
            sa.Column('organizer', sa.String(255), nullable=True),
            sa.Column('website', sa.String(512), nullable=True),
            sa.Column('flyer_url', sa.String(512), nullable=True),
            sa.Column('region', sa.String(100), nullable=True),
            sa.Column('distances', sa.ARRAY(sa.String()), nullable=True),
            sa.Column('ride_manager', sa.String(), nullable=True),
            sa.Column('manager_contact', sa.String(), nullable=True),
            sa.Column('event_type', sa.String(), nullable=True),
            sa.Column('event_details', sa.JSON(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('external_id', sa.String(), nullable=True),
            sa.Column('manager_email', sa.String(), nullable=True),
            sa.Column('manager_phone', sa.String(), nullable=True),
            sa.Column('judges', sa.ARRAY(sa.String()), nullable=True),
            sa.Column('directions', sa.Text(), nullable=True),
            sa.Column('map_link', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('is_canceled', sa.Boolean(), server_default=sa.text('false'), nullable=False),
            sa.Column('is_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False),
            sa.Column('source', sa.String(255), server_default=sa.text("'manual'"), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        # Create indexes that would normally exist
        op.create_index('ix_events_date_start', 'events', ['date_start'], unique=False)
        op.create_index('ix_events_id', 'events', ['id'], unique=False)
        op.create_index('ix_events_name', 'events', ['name'], unique=False)
        op.create_index('ix_events_region', 'events', ['region'], unique=False)
    
    # Add latitude and longitude columns to events table
    op.add_column('events', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('events', sa.Column('longitude', sa.Float(), nullable=True))
    
    # Add index on latitude and longitude for geospatial queries
    op.create_index(op.f('ix_events_latitude'), 'events', ['latitude'], unique=False)
    op.create_index(op.f('ix_events_longitude'), 'events', ['longitude'], unique=False)


def downgrade() -> None:
    # Remove indexes
    op.drop_index(op.f('ix_events_longitude'), table_name='events')
    op.drop_index(op.f('ix_events_latitude'), table_name='events')
    
    # Remove columns
    op.drop_column('events', 'longitude')
    op.drop_column('events', 'latitude') 