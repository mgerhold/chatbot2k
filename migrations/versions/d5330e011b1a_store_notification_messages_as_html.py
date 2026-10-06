"""store notification messages as html

Revision ID: d5330e011b1a
Revises: d1a4a0aa3ac3
Create Date: 2026-10-06 14:07:04.653629

"""

import html
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "d5330e011b1a"
down_revision: str | Sequence[str] | None = "d1a4a0aa3ac3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Notification messages used to be stored as plain text, but are now stored as HTML. Escape
    # existing messages so that they are displayed exactly as before.
    connection = op.get_bind()
    result = connection.execute(text("SELECT id, message FROM notification"))
    for id_, message in result.fetchall():
        connection.execute(
            text("UPDATE notification SET message = :message WHERE id = :id"),
            {"message": html.escape(message), "id": id_},
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Note: Any markup (e.g. links) in notifications created after the upgrade is kept as-is,
    # since there is no plain text equivalent.
    connection = op.get_bind()
    result = connection.execute(text("SELECT id, message FROM notification"))
    for id_, message in result.fetchall():
        connection.execute(
            text("UPDATE notification SET message = :message WHERE id = :id"),
            {"message": html.unescape(message), "id": id_},
        )
