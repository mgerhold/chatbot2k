from typing import Optional
from typing import final

from pydantic import BaseModel


@final
class BroadcastModel(BaseModel):
    interval_seconds: float
    message: str
    alias_command: Optional[str] = None


@final
class BroadcastsModel(BaseModel):
    broadcasts: list[BroadcastModel]
