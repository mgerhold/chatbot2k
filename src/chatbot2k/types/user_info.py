from typing import final

from pydantic import BaseModel
from pydantic import ConfigDict


@final
class UserInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    login: str
    display_name: str
