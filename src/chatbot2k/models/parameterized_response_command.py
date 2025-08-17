from typing import Literal
from typing import final

from pydantic import BaseModel


@final
class ParameterizedResponseCommandModel(BaseModel):
    type: Literal["parameterized"]
    name: str
    parameters: list[str]
    response: str
