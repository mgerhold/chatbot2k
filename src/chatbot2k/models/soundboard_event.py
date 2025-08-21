from typing import final

from pydantic.main import BaseModel


@final
class SoundboardEvent(BaseModel):
    clip_url: str
