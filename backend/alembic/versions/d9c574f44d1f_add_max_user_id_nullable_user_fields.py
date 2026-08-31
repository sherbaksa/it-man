"""add_max_user_id_nullable_user_fields

Revision ID: d9c574f44d1f
Revises: 564fc4e19487
Create Date: 2026-08-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9c574f44d1f'
down_revision: Union[str, None] = '564fc4e19487'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # B10: max_user_id — основной идентификатор теневого пользователя из MAX
    op.add_column(
        'user',
        sa.Column('max_user_id', sa.String(length=64), nullable=True),
    )
    op.create_index(
        op.f('ix_user_max_user_id'), 'user', ['max_user_id'], unique=True
    )

    # B10 (вариант B): у теневого пользователя из MAX нет отдела/логина/пароля —
    # снимаем NOT NULL, без синтетических заглушек
    op.alter_column('user', 'department_id', existing_type=sa.UUID(), nullable=True)
    op.alter_column(
        'user', 'login', existing_type=sa.String(length=100), nullable=True
    )
    op.alter_column(
        'user', 'password_hash', existing_type=sa.String(length=255), nullable=True
    )


def downgrade() -> None:
    op.alter_column(
        'user', 'password_hash', existing_type=sa.String(length=255), nullable=False
    )
    op.alter_column(
        'user', 'login', existing_type=sa.String(length=100), nullable=False
    )
    op.alter_column('user', 'department_id', existing_type=sa.UUID(), nullable=False)

    op.drop_index(op.f('ix_user_max_user_id'), table_name='user')
    op.drop_column('user', 'max_user_id')