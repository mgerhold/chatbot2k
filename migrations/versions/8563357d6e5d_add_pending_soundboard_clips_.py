"""add_pending_soundboard_clips_configuration_settings

Revision ID: 8563357d6e5d
Revises: bfd170595873
Create Date: 2026-01-02 12:25:59.121049

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8563357d6e5d"
down_revision: str | Sequence[str] | None = "bfd170595873"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Insert the new configuration settings with their default values
    connection = op.get_bind()

    # Check and insert MAX_PENDING_SOUNDBOARD_CLIPS
    result = connection.execute(
        sa.text("SELECT COUNT(*) FROM configurationsetting WHERE key = 'max_pending_soundboard_clips'")
    )
    count = result.scalar()

    if count == 0:
        config_table = sa.table(
            "configurationsetting",
            sa.column("key", sa.String()),
            sa.column("value", sa.String()),
        )
        op.execute(
            config_table.insert().values(
                key="max_pending_soundboard_clips",
                value="10",
            )
        )

    # Check and insert MAX_PENDING_SOUNDBOARD_CLIPS_PER_USER
    result = connection.execute(
        sa.text("SELECT COUNT(*) FROM configurationsetting WHERE key = 'max_pending_soundboard_clips_per_user'")
    )
    count = result.scalar()

    if count == 0:
        config_table = sa.table(
            "configurationsetting",
            sa.column("key", sa.String()),
            sa.column("value", sa.String()),
        )
        op.execute(
            config_table.insert().values(
                key="max_pending_soundboard_clips_per_user",
                value="2",
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Delete the configuration settings
    op.execute("DELETE FROM configurationsetting WHERE key = 'max_pending_soundboard_clips'")
    op.execute("DELETE FROM configurationsetting WHERE key = 'max_pending_soundboard_clips_per_user'")
