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
    # Add timezone support to datetime columns if not already present
    op.alter_column('events', 'date_start',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    existing_nullable=False)
    op.alter_column('events', 'date_end',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    existing_nullable=True)
    op.alter_column('events', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    existing_nullable=False,
                    server_default=sa.text('now()'))
    op.alter_column('events', 'updated_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    existing_nullable=True)

    # Ensure indexes exist (will not recreate if they already exist)
    op.create_index('ix_events_date_start', 'events', ['date_start'], unique=False, if_not_exists=True)
    op.create_index('ix_events_id', 'events', ['id'], unique=False, if_not_exists=True)
    op.create_index('ix_events_region', 'events', ['region'], unique=False, if_not_exists=True)


def downgrade() -> None:
    # Remove timezone support from datetime columns
    op.alter_column('events', 'date_start',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=False)
    op.alter_column('events', 'date_end',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=True)
    op.alter_column('events', 'created_at',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=False)
    op.alter_column('events', 'updated_at',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=True)
    
    # Drop indexes if they exist
    op.drop_index('ix_events_date_start', table_name='events', if_exists=True)
    op.drop_index('ix_events_id', table_name='events', if_exists=True)
    op.drop_index('ix_events_region', table_name='events', if_exists=True)
