"""add translation keys for soundboard clip suggestions

Revision ID: d73c2273194f
Revises: d5f3ea413035
Create Date: 2026-10-06 15:05:07.176592

"""

from collections.abc import Sequence
from typing import Final

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d73c2273194f"
down_revision: str | Sequence[str] | None = "d5f3ea413035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TRANSLATIONS: Final = {
    "SOUNDBOARD_CLIP_SUGGESTED": (
        "@{broadcaster} A new soundboard clip has just been suggested! Suggest your own at {soundboard_url}"
    ),
    "SOUNDBOARD_CLIP_SUGGESTED_BY_USER": (
        "@{broadcaster} @{uploader} has just suggested a new soundboard clip! Suggest your own at {soundboard_url}"
    ),
}


def upgrade() -> None:
    """Upgrade schema."""
    # Insert the new translation keys with their default values.
    # Only insert if they don't already exist.
    connection = op.get_bind()
    translation_table = sa.table(
        "translation",
        sa.column("key", sa.String()),
        sa.column("value", sa.String()),
    )
    for key, value in _TRANSLATIONS.items():
        result = connection.execute(sa.text("SELECT COUNT(*) FROM translation WHERE key = :key"), {"key": key})
        if result.scalar() == 0:
            op.execute(translation_table.insert().values(key=key, value=value))


def downgrade() -> None:
    """Downgrade schema."""
    # Delete the translation entries.
    connection = op.get_bind()
    for key in _TRANSLATIONS:
        connection.execute(sa.text("DELETE FROM translation WHERE key = :key"), {"key": key})
