from enum import Enum
from enum import auto
from typing import final


@final
class TokenType(Enum):
    COLON = auto()
    COMMA = auto()
    DOLLAR = auto()
    EXCLAMATION_MARK = auto()
    HASH = auto()
    SEMICOLON = auto()
    EQUALS = auto()
    EQUALS_EQUALS = auto()
    EXCLAMATION_MARK_EQUALS = auto()
    LESS_THAN = auto()
    LESS_THAN_EQUALS = auto()
    GREATER_THAN = auto()
    GREATER_THAN_EQUALS = auto()
    PLUS = auto()
    MINUS = auto()
    ASTERISK = auto()
    PERCENT = auto()
    QUESTION_MARK = auto()
    SLASH = auto()
    LEFT_PARENTHESIS = auto()
    RIGHT_PARENTHESIS = auto()
    LEFT_SQUARE_BRACKET = auto()
    RIGHT_SQUARE_BRACKET = auto()

    STORE = auto()
    PARAMS = auto()
    PRINT = auto()
    LET = auto()

    IDENTIFIER = auto()
    STRING_LITERAL = auto()
    NUMBER_LITERAL = auto()
    BOOL_LITERAL = auto()

    STRING = auto()
    NUMBER = auto()
    BOOL = auto()
    LIST = auto()

    AND = auto()
    OR = auto()
    NOT = auto()

    FOR = auto()
    AS = auto()
    IF = auto()
    YEET = auto()
    COLLECT = auto()
    WITH = auto()

    END_OF_INPUT = auto()
