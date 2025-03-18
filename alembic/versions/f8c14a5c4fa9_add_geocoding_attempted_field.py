"""Add geocoding_attempted field

Revision ID: f8c14a5c4fa9
Revises: add_lat_long_to_events
Create Date: 2025-03-18 16:21:50.037537

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f8c14a5c4fa9'
down_revision = 'add_lat_long_to_events'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add geocoding_attempted column with default False
    op.add_column('events', sa.Column('geocoding_attempted', sa.Boolean(), 
                                    server_default=sa.text('false'), 
                                    nullable=False))
    op.create_index(op.f('ix_events_geocoding_attempted'), 'events', ['geocoding_attempted'], unique=False)


def downgrade() -> None:
    # Remove the geocoding_attempted column
    op.drop_index(op.f('ix_events_geocoding_attempted'), table_name='events')
    op.drop_column('events', 'geocoding_attempted')
