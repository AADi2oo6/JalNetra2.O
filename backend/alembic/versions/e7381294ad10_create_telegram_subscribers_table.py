"""create_telegram_subscribers_table

Revision ID: e7381294ad10
Revises: dc2465f62429
Create Date: 2026-10-16 14:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7381294ad10'
down_revision: Union[str, Sequence[str], None] = 'dc2465f62429'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'telegram_subscribers',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('chat_type', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_telegram_subscribers_chat_id', 'telegram_subscribers', ['chat_id'], unique=True)
    op.create_index('ix_telegram_subscribers_is_active', 'telegram_subscribers', ['is_active'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_telegram_subscribers_is_active', table_name='telegram_subscribers')
    op.drop_index('ix_telegram_subscribers_chat_id', table_name='telegram_subscribers')
    op.drop_table('telegram_subscribers')
