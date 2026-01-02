"""add_soundboard_managed_via_web_ui_translation

Revision ID: 153518e030e6
Revises: 813b0a6fbf32
Create Date: 2026-01-02 11:11:05.274340

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "153518e030e6"
down_revision: str | Sequence[str] | None = "813b0a6fbf32"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Insert the new translation key with its default value
    # Only insert if it doesn't already exist
    connection = op.get_bind()
    result = connection.execute(
        sa.text("SELECT COUNT(*) FROM translation WHERE key = 'SOUNDBOARD_MANAGED_VIA_WEB_UI'")
    )
    count = result.scalar()

    if count == 0:
        translation_table = sa.table(
            "translation",
            sa.column("key", sa.String()),
            sa.column("value", sa.String()),
        )
        op.execute(
            translation_table.insert().values(
                key="SOUNDBOARD_MANAGED_VIA_WEB_UI",
                value="Soundboard clips are managed exclusively via the web UI.",
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Delete the translation entry
    op.execute("DELETE FROM translation WHERE key = 'SOUNDBOARD_MANAGED_VIA_WEB_UI'")
