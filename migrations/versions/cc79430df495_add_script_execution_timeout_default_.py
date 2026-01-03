"""add script_execution_timeout default value

Revision ID: cc79430df495
Revises: ef67d17c9d30
Create Date: 2026-01-03 17:33:52.703575

"""

from collections.abc import Sequence
from typing import Final

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cc79430df495"
down_revision: str | Sequence[str] | None = "ef67d17c9d30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    configuration_setting_table: Final = sa.table(
        "configurationsetting",
        sa.column("key", sa.String()),
        sa.column("value", sa.String()),
    )

    op.bulk_insert(
        configuration_setting_table,
        [
            {
                "key": "script_execution_timeout",
                "value": "30",
            },
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
