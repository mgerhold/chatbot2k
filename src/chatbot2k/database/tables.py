from typing import Optional
from typing import final

from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlmodel import Field
from sqlmodel import Relationship
from sqlmodel import SQLModel

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
