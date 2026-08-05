"""factory: chains of machines, ordered lists

Revision ID: a2fb784ac10c
Revises: e6edaa055ac5
Create Date: 2026-08-05 19:03:13.957991

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a2fb784ac10c'
down_revision: Union[str, None] = 'e6edaa055ac5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('machine_chains',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('last_settled_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_machine_chains_user_id'), 'machine_chains', ['user_id'], unique=False)

    # Existing machines belonged to the old independent-machine model and
    # have no chain to join - there's no sensible default chain_id, and
    # this is dev data, so start fresh rather than inventing one.
    op.execute('DELETE FROM machines')

    op.add_column('machines', sa.Column('chain_id', sa.Integer(), nullable=False))
    op.add_column('machines', sa.Column('position', sa.Integer(), nullable=False))
    op.drop_index('ix_machines_user_id', table_name='machines')
    op.create_index(op.f('ix_machines_chain_id'), 'machines', ['chain_id'], unique=False)
    op.drop_constraint('machines_user_id_fkey', 'machines', type_='foreignkey')
    op.create_foreign_key('machines_chain_id_fkey', 'machines', 'machine_chains', ['chain_id'], ['id'], ondelete='CASCADE')
    op.drop_column('machines', 'active')
    op.drop_column('machines', 'last_settled_at')
    op.drop_column('machines', 'user_id')


def downgrade() -> None:
    op.execute('DELETE FROM machines')

    op.add_column('machines', sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.add_column('machines', sa.Column('last_settled_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False))
    op.add_column('machines', sa.Column('active', sa.BOOLEAN(), server_default=sa.text('true'), autoincrement=False, nullable=False))
    op.drop_constraint('machines_chain_id_fkey', 'machines', type_='foreignkey')
    op.create_foreign_key('machines_user_id_fkey', 'machines', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.drop_index(op.f('ix_machines_chain_id'), table_name='machines')
    op.create_index('ix_machines_user_id', 'machines', ['user_id'], unique=False)
    op.drop_column('machines', 'position')
    op.drop_column('machines', 'chain_id')
    op.drop_index(op.f('ix_machine_chains_user_id'), table_name='machine_chains')
    op.drop_table('machine_chains')
