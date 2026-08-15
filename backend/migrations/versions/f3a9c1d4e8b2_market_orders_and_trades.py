"""market: orders and trades

Revision ID: f3a9c1d4e8b2
Revises: a2fb784ac10c
Create Date: 2026-08-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f3a9c1d4e8b2'
down_revision: Union[str, None] = 'a2fb784ac10c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('reserved_balance', sa.Numeric(18, 4), server_default='0', nullable=False))

    op.create_table('market_orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('resource_id', sa.Integer(), nullable=False),
    sa.Column('side', sa.String(length=4), nullable=False),
    sa.Column('price', sa.Numeric(18, 4), nullable=False),
    sa.Column('original_quantity', sa.Integer(), nullable=False),
    sa.Column('remaining_quantity', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=16), server_default='open', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['resource_id'], ['resource_definitions.id']),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_market_orders_user_id'), 'market_orders', ['user_id'], unique=False)
    op.create_index(op.f('ix_market_orders_resource_id'), 'market_orders', ['resource_id'], unique=False)
    op.create_index(op.f('ix_market_orders_created_at'), 'market_orders', ['created_at'], unique=False)

    op.create_table('trades',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('resource_id', sa.Integer(), nullable=False),
    sa.Column('buyer_id', sa.Integer(), nullable=False),
    sa.Column('seller_id', sa.Integer(), nullable=False),
    sa.Column('buy_order_id', sa.Integer(), nullable=False),
    sa.Column('sell_order_id', sa.Integer(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('price', sa.Numeric(18, 4), nullable=False),
    sa.Column('total_value', sa.Numeric(18, 4), nullable=False),
    sa.Column('fee', sa.Numeric(18, 4), server_default='0', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['resource_id'], ['resource_definitions.id']),
    sa.ForeignKeyConstraint(['buyer_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['seller_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['buy_order_id'], ['market_orders.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['sell_order_id'], ['market_orders.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trades_resource_id'), 'trades', ['resource_id'], unique=False)
    op.create_index(op.f('ix_trades_buyer_id'), 'trades', ['buyer_id'], unique=False)
    op.create_index(op.f('ix_trades_seller_id'), 'trades', ['seller_id'], unique=False)
    op.create_index(op.f('ix_trades_created_at'), 'trades', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_trades_created_at'), table_name='trades')
    op.drop_index(op.f('ix_trades_seller_id'), table_name='trades')
    op.drop_index(op.f('ix_trades_buyer_id'), table_name='trades')
    op.drop_index(op.f('ix_trades_resource_id'), table_name='trades')
    op.drop_table('trades')

    op.drop_index(op.f('ix_market_orders_created_at'), table_name='market_orders')
    op.drop_index(op.f('ix_market_orders_resource_id'), table_name='market_orders')
    op.drop_index(op.f('ix_market_orders_user_id'), table_name='market_orders')
    op.drop_table('market_orders')

    op.drop_column('users', 'reserved_balance')
