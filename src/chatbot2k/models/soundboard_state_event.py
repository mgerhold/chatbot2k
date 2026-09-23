from typing import final

from pydantic.main import BaseModel


@final
class SoundboardStateEvent(BaseModel):
    is_enabled: bool
