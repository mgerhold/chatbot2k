"""Add new translation key

Revision ID: 51019a3ea980
Revises: 5f9af2cc10f5
Create Date: 2026-03-14 15:58:51.374590

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "51019a3ea980"
down_revision: str | Sequence[str] | None = "5f9af2cc10f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Insert the new translation key with its default value
    # Only insert if it doesn't already exist
    connection = op.get_bind()
    result = connection.execute(
        sa.text("SELECT COUNT(*) FROM translation WHERE key = 'COMMAND_UPDATE_CAUSES_AMBIGUITY'")
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
                key="COMMAND_UPDATE_CAUSES_AMBIGUITY",
                value="Updating this command will cause ambiguity with other commands.",
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Delete the translation entry
    op.execute("DELETE FROM translation WHERE key = 'COMMAND_UPDATE_CAUSES_AMBIGUITY'")
