"""add_cannot_add_or_update_script_command_translation

Revision ID: 584e818241dd
Revises: c96656cce2d6
Create Date: 2025-11-10 17:16:36.829658

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "584e818241dd"
down_revision: str | Sequence[str] | None = "c96656cce2d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # For SQLite, we need to recreate the table with the new enum values
    # First, create a new enum type with the additional value
    with op.batch_alter_table("translation", schema=None) as batch_op:
        batch_op.alter_column(
            "key",
            existing_type=sa.Enum(
                "COMMAND_ALREADY_EXISTS",
                "COMMAND_TO_UPDATE_NOT_FOUND",
                "COMMAND_TO_DELETE_NOT_FOUND",
                "BUILTIN_COMMAND_CANNOT_BE_DELETED",
                "BUILTIN_COMMAND_CANNOT_BE_CHANGED",
                "COMMAND_ADDED",
                "COMMAND_UPDATED",
                "COMMAND_REMOVED",
                "SOUNDBOARD_ENABLED",
                "SOUNDBOARD_DISABLED",
                "CANNOT_ADD_OR_UPDATE_SOUNDBOARD_COMMAND",
                name="translationkey",
            ),
            type_=sa.Enum(
                "COMMAND_ALREADY_EXISTS",
                "COMMAND_TO_UPDATE_NOT_FOUND",
                "COMMAND_TO_DELETE_NOT_FOUND",
                "BUILTIN_COMMAND_CANNOT_BE_DELETED",
                "BUILTIN_COMMAND_CANNOT_BE_CHANGED",
                "COMMAND_ADDED",
                "COMMAND_UPDATED",
                "COMMAND_REMOVED",
                "SOUNDBOARD_ENABLED",
                "SOUNDBOARD_DISABLED",
                "CANNOT_ADD_OR_UPDATE_SOUNDBOARD_COMMAND",
                "CANNOT_ADD_OR_UPDATE_SCRIPT_COMMAND",
                name="translationkey",
            ),
            existing_nullable=False,
        )

    # Insert the new translation key with its default value
    translation_table = sa.table(
        "translation",
        sa.column("key", sa.String()),
        sa.column("value", sa.String()),
    )
    op.execute(
        translation_table.insert().values(
            key="CANNOT_ADD_OR_UPDATE_SCRIPT_COMMAND",
            value=(
                "You cannot add or update a script command this way. Use `remove` and "
                + "`add-script` as subcommands instead."
            ),
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Delete the translation entry
    op.execute("DELETE FROM translation WHERE key = 'CANNOT_ADD_OR_UPDATE_SCRIPT_COMMAND'")

    # Revert the enum type to the old values
    with op.batch_alter_table("translation", schema=None) as batch_op:
        batch_op.alter_column(
            "key",
            existing_type=sa.Enum(
                "COMMAND_ALREADY_EXISTS",
                "COMMAND_TO_UPDATE_NOT_FOUND",
                "COMMAND_TO_DELETE_NOT_FOUND",
                "BUILTIN_COMMAND_CANNOT_BE_DELETED",
                "BUILTIN_COMMAND_CANNOT_BE_CHANGED",
                "COMMAND_ADDED",
                "COMMAND_UPDATED",
                "COMMAND_REMOVED",
                "SOUNDBOARD_ENABLED",
                "SOUNDBOARD_DISABLED",
                "CANNOT_ADD_OR_UPDATE_SOUNDBOARD_COMMAND",
                "CANNOT_ADD_OR_UPDATE_SCRIPT_COMMAND",
                name="translationkey",
            ),
            type_=sa.Enum(
                "COMMAND_ALREADY_EXISTS",
                "COMMAND_TO_UPDATE_NOT_FOUND",
                "COMMAND_TO_DELETE_NOT_FOUND",
                "BUILTIN_COMMAND_CANNOT_BE_DELETED",
                "BUILTIN_COMMAND_CANNOT_BE_CHANGED",
                "COMMAND_ADDED",
                "COMMAND_UPDATED",
                "COMMAND_REMOVED",
                "SOUNDBOARD_ENABLED",
                "SOUNDBOARD_DISABLED",
                "CANNOT_ADD_OR_UPDATE_SOUNDBOARD_COMMAND",
                name="translationkey",
            ),
            existing_nullable=False,
        )
