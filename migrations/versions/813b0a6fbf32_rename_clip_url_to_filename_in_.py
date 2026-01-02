"""rename clip_url to filename in soundboard table

Revision ID: 813b0a6fbf32
Revises: 6a0fbce552ad
Create Date: 2026-01-02 09:47:49.433177

"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "813b0a6fbf32"
down_revision: str | Sequence[str] | None = "6a0fbce552ad"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Get database connection
    connection = op.get_bind()

    # First, fetch all existing soundboard commands
    result = connection.execute(text("SELECT name, clip_url FROM soundboardcommand"))
    soundboard_commands = result.fetchall()

    # Extract filenames from URLs/paths and update each record
    for name, clip_url in soundboard_commands:
        # Extract just the filename from the URL or path
        # Handle both absolute URLs (https://...) and relative paths (static/...)
        filename = clip_url.split("/")[-1].split("?")[0]  # Get last part after /, remove query params

        # Update the record with just the filename
        connection.execute(
            text("UPDATE soundboardcommand SET clip_url = :filename WHERE name = :name"),
            {"filename": filename, "name": name},
        )

    # Now rename the column from clip_url to filename
    with op.batch_alter_table("soundboardcommand", schema=None) as batch_op:
        batch_op.alter_column("clip_url", new_column_name="filename")


def downgrade() -> None:
    """Downgrade schema."""
    # Rename the column back from filename to clip_url
    with op.batch_alter_table("soundboardcommand", schema=None) as batch_op:
        batch_op.alter_column("filename", new_column_name="clip_url")

    # Note: We cannot restore the original full URLs/paths as that information
    # is lost during the upgrade. The downgrade will only rename the column back,
    # but the values will still be just filenames.
