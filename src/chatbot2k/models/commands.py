from typing import final

from pydantic.main import BaseModel

from chatbot2k.models.command_model import CommandModel


@final
class CommandsModel(BaseModel):
    commands: list[CommandModel]
