from enum import Enum
from enum import auto
from typing import final


@final
class TokenType(Enum):
    COMMA = auto()
    DOLLAR = auto()
    EXCLAMATION_MARK = auto()
    SEMICOLON = auto()
    EQUALS = auto()
    PLUS = auto()
    MINUS = auto()
    ASTERISK = auto()
    SLASH = auto()
    LEFT_PARENTHESIS = auto()
    RIGHT_PARENTHESIS = auto()

    STORE = auto()
    PARAMS = auto()
    PRINT = auto()
    LET = auto()

    IDENTIFIER = auto()
    STRING_LITERAL = auto()
    NUMBER_LITERAL = auto()

    END_OF_INPUT = auto()
