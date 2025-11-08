from enum import Enum
from enum import auto
from typing import final


@final
class TokenType(Enum):
    SEMICOLON = auto()
    EQUALS = auto()
    PLUS = auto()
    MINUS = auto()
    ASTERISK = auto()
    SLASH = auto()

    STORE = auto()
    PRINT = auto()

    IDENTIFIER = auto()
    STRING_LITERAL = auto()
    NUMBER_LITERAL = auto()

    END_OF_INPUT = auto()
