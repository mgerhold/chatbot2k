from typing import Final

from alembic import command
from alembic.config import Config


def upgrade_to_head(*, database_url: str) -> None:
    config: Final = Config()
    config.set_main_option("script_location", "./migrations")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
