"""Use message ID as primary key for received Twitch messages

Revision ID: 9701b4272c26
Revises: cc340445a4ca
Create Date: 2026-01-04 14:09:41.942912

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9701b4272c26"
down_revision: str | Sequence[str] | None = "cc340445a4ca"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite doesn't support altering primary keys directly, so we recreate the table
    with op.batch_alter_table(
        "receivedtwitchmessage",
        recreate="always",
        table_args=(sa.PrimaryKeyConstraint("message_id", name=op.f("pk_receivedtwitchmessage")),),
    ) as batch_op:
        batch_op.drop_column("id")


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate the table with the old structure (id as primary key)
    with op.batch_alter_table(
        "receivedtwitchmessage",
        recreate="always",
        table_args=(sa.PrimaryKeyConstraint("id", name=op.f("pk_receivedtwitchmessage")),),
    ) as batch_op:
        batch_op.add_column(sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True))
