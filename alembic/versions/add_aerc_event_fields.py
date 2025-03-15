"""add AERC event fields

Revision ID: [generate_uuid_here]
Revises: [previous_revision_id]
Create Date: [current_date]

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY


# revision identifiers, used by Alembic.
revision = '[generate_uuid_here]'
down_revision = '[previous_revision_id]'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('events', sa.Column('ride_manager', sa.String(), nullable=True))
    op.add_column('events', sa.Column('manager_email', sa.String(), nullable=True))
    op.add_column('events', sa.Column('manager_phone', sa.String(), nullable=True))
    op.add_column('events', sa.Column('judges', ARRAY(sa.String()), nullable=True))
    op.add_column('events', sa.Column('directions', sa.Text(), nullable=True))
    op.add_column('events', sa.Column('map_link', sa.String(), nullable=True))
    op.add_column('events', sa.Column('external_id', sa.String(), nullable=True))


def downgrade():
    op.drop_column('events', 'ride_manager')
    op.drop_column('events', 'manager_email')
    op.drop_column('events', 'manager_phone')
    op.drop_column('events', 'judges')
    op.drop_column('events', 'directions')
    op.drop_column('events', 'map_link')
    op.drop_column('events', 'external_id')
