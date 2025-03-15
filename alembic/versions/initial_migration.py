"""Initial migration

Revision ID: initial_migration
Revises: 
Create Date: 2023-12-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'initial_migration'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create events table
    op.create_table(
        'events',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('location', sa.String(255), nullable=False),
        sa.Column('date_start', sa.DateTime(), nullable=False, index=True),
        sa.Column('date_end', sa.DateTime(), nullable=True),
        sa.Column('organizer', sa.String(255), nullable=True),
        sa.Column('website', sa.String(512), nullable=True),
        sa.Column('flyer_url', sa.String(512), nullable=True),
        sa.Column('region', sa.String(100), nullable=True, index=True),
        sa.Column('distances', sa.ARRAY(sa.String), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('events')
