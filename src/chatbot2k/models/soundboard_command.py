from typing import Literal
from typing import final

from pydantic.main import BaseModel


@final
class SoundboardCommandModel(BaseModel):
    type: Literal["soundboard"] = "soundboard"
    name: str
    clip_url: str
