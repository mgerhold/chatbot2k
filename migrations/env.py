import os
from logging.config import fileConfig
from pathlib import Path
from typing import Literal

from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlmodel import SQLModel

from chatbot2k.config import DATABASE_FILE_ENV_VARIABLE
from chatbot2k.database.engine import create_database_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

db_file_path = os.getenv(DATABASE_FILE_ENV_VARIABLE)
if db_file_path is not None:
    db_url = create_database_url(Path(db_file_path))
    config.set_main_option("sqlalchemy.url", db_url)


target_metadata = SQLModel.metadata


def _render_item(type_: str, obj: object, autogen_context: object | None) -> str | Literal[False]:
    # Whenever Alembic tries to render a column "type", and it is SQLModel's AutoString,
    # render it as plain sa.String() so type checkers are happy and the DDL is portable.
    if type_ == "type":
        cls = obj.__class__
        if cls.__module__ == "sqlmodel.sql.sqltypes" and cls.__name__ == "AutoString":
            return "sa.String()"
    return False  # use default rendering otherwise


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=_render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_item=_render_item,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
