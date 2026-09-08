"""add monitoring status history

Revision ID: e8cff9f59e6b
Revises: d9c574f44d1f
Create Date: 2026-09-08 00:49:22.324039

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e8cff9f59e6b'
down_revision: Union[str, None] = 'd9c574f44d1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('monitoring_status_history',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('host_identifier', sa.String(length=255), nullable=False),
    sa.Column(
        'status',
        postgresql.ENUM('ok', 'warning', 'critical', 'unknown', name='monitoring_health_status', create_type=False),
        nullable=False,
    ),
    sa.Column('last_value', sa.Text(), nullable=True),
    sa.Column(
        'source',
        postgresql.ENUM('zabbix', 'kaspersky', name='monitoring_source', create_type=False),
        nullable=False,
    ),
    sa.Column('checked_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_monitoring_status_history_host_checked', 'monitoring_status_history', ['host_identifier', 'checked_at'], unique=False)
    op.add_column('monitoring_status', sa.Column('history_retention_hours', sa.Integer(), nullable=True, comment='Глубина хранения истории в часах для этого хоста; NULL = использовать settings.MONITORING_HISTORY_DEFAULT_RETENTION_HOURS. Задаётся вручную для хостов, требующих более глубокой истории (серверы, сетевые шары), в отличие от рядовых хостов, где интересна только оперативная картина (см. B12).'))
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_column('monitoring_status', 'history_retention_hours')
    op.drop_index('ix_monitoring_status_history_host_checked', table_name='monitoring_status_history')
    op.drop_table('monitoring_status_history')
    # ### end Alembic commands ###
