"""add AERC event fields
Revision ID: add_aerc_event_fields
Revises: add_flexible_event_fields
Create Date: 2024-03-15 20:11:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

# revision identifiers, used by Alembic.
revision = 'add_aerc_event_fields'
down_revision = 'add_flexible_event_fields'
branch_labels = None
depends_on = None

def upgrade():
    # These columns are already added in add_flexible_event_fields.py
    # op.add_column('events', sa.Column('ride_manager', sa.String(), nullable=True))
    # op.add_column('events', sa.Column('external_id', sa.String(), nullable=True))
    
    # Add new AERC-specific columns
    op.add_column('events', sa.Column('manager_email', sa.String(), nullable=True))
    op.add_column('events', sa.Column('manager_phone', sa.String(), nullable=True))
    op.add_column('events', sa.Column('judges', ARRAY(sa.String()), nullable=True))
    op.add_column('events', sa.Column('directions', sa.Text(), nullable=True))
    op.add_column('events', sa.Column('map_link', sa.String(), nullable=True))

def downgrade():
    # Don't drop ride_manager and external_id as they're managed by add_flexible_event_fields.py
    op.drop_column('events', 'manager_email')
    op.drop_column('events', 'manager_phone')
    op.drop_column('events', 'judges')
    op.drop_column('events', 'directions')
    op.drop_column('events', 'map_link')
