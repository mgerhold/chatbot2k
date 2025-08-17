from typing import final

from pydantic.main import BaseModel


@final
class ConstantModel(BaseModel):
    name: str
    text: str


@final
class ConstantsModel(BaseModel):
    constants: list[ConstantModel]
