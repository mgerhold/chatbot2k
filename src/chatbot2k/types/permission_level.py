from enum import IntEnum
from typing import final


@final
class PermissionLevel(IntEnum):
    VIEWER = 0
    MODERATOR = 1
    ADMIN = 2
