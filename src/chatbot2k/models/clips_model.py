from typing import final

from pydantic import BaseModel

from chatbot2k.models.clip_model import ClipModel


@final
class ClipsModel(BaseModel):
    clips: list[ClipModel]
