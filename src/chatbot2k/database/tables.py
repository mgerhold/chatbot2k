from typing import Optional
from typing import final

from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlmodel import Field
from sqlmodel import Relationship

from chatbot2k.database.metadata import SQLModel
from chatbot2k.translation_key import TranslationKey


@final
class StaticCommand(SQLModel, table=True):
    name: str = Field(primary_key=True)
    response: str


@final
class Parameter(SQLModel, table=True):
    command_name: str = Field(
        sa_column=Column(
            "command_name",
            String,
            ForeignKey("parameterizedcommand.name", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    name: str = Field(primary_key=True)

    command: "ParameterizedCommand" = Relationship(back_populates="parameters")


@final
class ParameterizedCommand(SQLModel, table=True):
    name: str = Field(primary_key=True, index=True)
    response: str

    parameters: list[Parameter] = Relationship(
        back_populates="command",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


@final
class SoundboardCommand(SQLModel, table=True):
    name: str = Field(primary_key=True)
    clip_url: str


@final
class Broadcast(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    interval_seconds: int
    message: str
    alias_command: Optional[str]


@final
class Constant(SQLModel, table=True):
    name: str = Field(primary_key=True)
    text: str


@final
class DictionaryEntry(SQLModel, table=True):
    word: str = Field(primary_key=True)
    explanation: str


@final
class Translation(SQLModel, table=True):
    key: TranslationKey = Field(primary_key=True)
    value: str


@final
class Script(SQLModel, table=True):
    """Represents a script command in the database.

    The command name serves as the primary key (e.g., '!run-script', '!increase-counter').
    The script is stored as JSON (dumped Pydantic model) and the source code is preserved.
    """

    command: str = Field(primary_key=True)
    source_code: str  # Original source code.
    script_json: str  # JSON representation of the Script Pydantic model.

    stores: list["ScriptStore"] = Relationship(
        back_populates="script",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


@final
class ScriptStore(SQLModel, table=True):
    """Represents a store (persistent variable) for a script.

    Primary key is the combination of `script_command` and `store_name`.
    Contains the store definition (from AST) and the current runtime value.
    """

    script_command: str = Field(
        sa_column=Column(
            "script_command",
            String,
            ForeignKey("script.command", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    store_name: str = Field(primary_key=True)
    store_json: str  # JSON representation of the `Store` Pydantic model (from AST).
    value_json: str  # JSON representation of the current `Value`.

    script: Script = Relationship(back_populates="stores")


@final
class TwitchTokenSet(SQLModel, table=True):
    """Represents a set of Twitch tokens for API access."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str
    access_token: str
    refresh_token: str
    expires_at: int  # Unix timestamp of expiration time.
