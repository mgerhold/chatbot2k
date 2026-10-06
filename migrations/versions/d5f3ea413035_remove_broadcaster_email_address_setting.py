"""remove broadcaster email address setting

Revision ID: d5f3ea413035
Revises: d5330e011b1a
Create Date: 2026-10-06 14:19:30.395637

"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "d5f3ea413035"
down_revision: str | Sequence[str] | None = "d5330e011b1a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # The broadcaster is now notified via the regular notification system (and the email
    # address of their verified user profile), so this setting is no longer used.
    op.get_bind().execute(text("DELETE FROM configurationsetting WHERE key = 'broadcaster_email_address'"))


def downgrade() -> None:
    """Downgrade schema."""
    # Note: The deleted email address cannot be restored. Older versions treat a missing
    # setting as "not configured".
    pass
