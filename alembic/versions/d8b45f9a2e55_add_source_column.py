"""add source column

Revision ID: d8b45f9a2e55
Revises: 7150513a9155
Create Date: 2024-03-15 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd8b45f9a2e55'
down_revision = '7150513a9155'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add source column with default value for existing records
    op.add_column('events', sa.Column('source', sa.String(length=50), nullable=False, 
                                    server_default='manual'))
    # Create an index on source for efficient querying
    op.create_index(op.f('ix_events_source'), 'events', ['source'], unique=False)


def downgrade() -> None:
    # Remove the source column
    op.drop_index(op.f('ix_events_source'), table_name='events')
    op.drop_column('events', 'source')