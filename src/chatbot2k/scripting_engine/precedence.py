from enum import IntEnum
from enum import auto
from typing import final


@final
class Precedence(IntEnum):
    # From weakest to strongest.
    UNKNOWN = auto()
    TERNARY = auto()
    OR = auto()
    AND = auto()
    EQUALITY = auto()
    COMPARISON = auto()
    SUM = auto()
    PRODUCT = auto()
    UNARY = auto()
    CALL = auto()
