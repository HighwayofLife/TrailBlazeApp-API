"""add flexible event fields

Revision ID: [generate_uuid_here]
Revises: [previous_revision_id]
Create Date: [current_date]

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '[generate_uuid_here]'
down_revision = '[previous_revision_id]'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('events', sa.Column('ride_manager', sa.String(), nullable=True))
    op.add_column('events', sa.Column('manager_contact', sa.String(), nullable=True))
    op.add_column('events', sa.Column('event_type', sa.String(), nullable=True))
    op.add_column('events', sa.Column('event_details', JSONB(), nullable=True))
    op.add_column('events', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('events', sa.Column('external_id', sa.String(), nullable=True))


def downgrade():
    op.drop_column('events', 'ride_manager')
    op.drop_column('events', 'manager_contact')
    op.drop_column('events', 'event_type')
    op.drop_column('events', 'event_details')
    op.drop_column('events', 'notes')
    op.drop_column('events', 'external_id')
