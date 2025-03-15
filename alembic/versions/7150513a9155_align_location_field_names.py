"""align_location_field_names

Revision ID: 7150513a9155
Revises: rename_date_columns
Create Date: 2025-03-15 21:02:11.545201

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7150513a9155'
down_revision = 'rename_date_columns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create new events table with all columns
    op.create_table('events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=False),
        sa.Column('date_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('date_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('organizer', sa.String(length=255), nullable=True),
        sa.Column('website', sa.String(length=512), nullable=True),
        sa.Column('flyer_url', sa.String(length=512), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('distances', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
        sa.Column('ride_manager', sa.String(), nullable=True),
        sa.Column('manager_contact', sa.String(), nullable=True),
        sa.Column('event_type', sa.String(), nullable=True),
        sa.Column('event_details', postgresql.JSONB(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('external_id', sa.String(), nullable=True),
        sa.Column('manager_email', sa.String(), nullable=True),
        sa.Column('manager_phone', sa.String(), nullable=True),
        sa.Column('judges', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('directions', sa.Text(), nullable=True),
        sa.Column('map_link', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_events_date_start', 'events', ['date_start'], unique=False)
    op.create_index('ix_events_id', 'events', ['id'], unique=False)
    op.create_index('ix_events_region', 'events', ['region'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_events_date_start', table_name='events')
    op.drop_index('ix_events_id', table_name='events')
    op.drop_index('ix_events_region', table_name='events')
    op.drop_table('events')
