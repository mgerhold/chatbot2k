from typing import Literal
from typing import final

from pydantic import BaseModel


@final
class StaticResponseCommandModel(BaseModel):
    type: Literal["static"]
    name: str
    response: str
