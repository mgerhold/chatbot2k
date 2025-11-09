from enum import IntEnum
from typing import final


@final
class Precedence(IntEnum):
    UNKNOWN = 0
    SUM = 1
    PRODUCT = 2
    UNARY = 3
