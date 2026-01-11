from datetime import datetime
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
class ConfigurationSetting(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str


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
    filename: str
    uploader_twitch_id: Optional[str] = Field(default=None)
    uploader_twitch_login: Optional[str] = Field(default=None)
    uploader_twitch_display_name: Optional[str] = Field(default=None)


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


@final
class LiveNotificationChannel(SQLModel, table=True):
    """Represents a Twitch channel to be monitored for notifications when going live."""

    id: Optional[int] = Field(default=None, primary_key=True)
    broadcaster_id: str
    text_template: str
    target_channel: str  # Name of the channel (usually on Discord) to send the notification to.


@final
class PendingSoundboardClip(SQLModel, table=True):
    """Represents a pending soundboard clip upload."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    filename: str
    uploader_twitch_id: str
    uploader_twitch_login: str
    uploader_twitch_display_name: str
    may_persist_uploader_info: bool


@final
class EntranceSound(SQLModel, table=True):
    """Represents an entrance sound configuration for a Twitch user."""

    twitch_user_id: str = Field(primary_key=True)
    filename: str


@final
class CachedSourceCode(SQLModel, table=True):
    """Represents cached source code for scripts to optimize performance."""

    url: str = Field(primary_key=True)
    source_code: str


@final
class ReceivedTwitchMessage(SQLModel, table=True):
    """Represents a record of received Twitch messages to prevent duplicate processing."""

    message_id: str = Field(primary_key=True)
    timestamp: datetime


@final
class UserProfile(SQLModel, table=True):
    """Represents a user profile with customizable settings."""

    twitch_user_id: str = Field(primary_key=True)
    email: Optional[str] = None
    email_is_verified: bool = False


@final
class EmailVerificationToken(SQLModel, table=True):
    """Represents an email verification token for user profiles."""

    token: str = Field(primary_key=True)
    twitch_user_id: str
    created_at: datetime


@final
class Notification(SQLModel, table=True):
    """Represents a notification that has been sent to a user."""

    id: Optional[int] = Field(default=None, primary_key=True)
    twitch_user_id: str
    message: str
    sent_at: datetime
    has_been_read: bool
