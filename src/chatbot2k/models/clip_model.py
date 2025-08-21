from typing import final

from pydantic.main import BaseModel


@final
class ClipModel(BaseModel):
    name: str
    clip_url: str
