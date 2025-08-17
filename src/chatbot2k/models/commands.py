from typing import final

from pydantic.main import BaseModel

from chatbot2k.models.parameterized_response_command import ParameterizedResponseCommandModel
from chatbot2k.models.static_response_command import StaticResponseCommandModel


@final
class CommandsModel(BaseModel):
    commands: list[StaticResponseCommandModel | ParameterizedResponseCommandModel]
