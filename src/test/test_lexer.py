from typing import Final

import pytest

from chatbot2k.scripting_engine.lexer import Lexer
from chatbot2k.scripting_engine.lexer import LexerError
from chatbot2k.scripting_engine.source_location import SourceLocation
from chatbot2k.scripting_engine.token import Token
from chatbot2k.scripting_engine.token_types import TokenType


def _tokenize_source(source: str) -> list[Token]:
    lexer: Final = Lexer(source)
    return lexer.tokenize()


def test_tokenize_can_analyze_all_token_types() -> None:
    source: Final = (
        r";=+-*%/()STORE PRINT some_identifier_123 'my string 🐍\'quoted\'\ntext on second line' 3.14 "
        + "LET PARAMS,$!:?true false== != < <= > >= ..= ..< and or not#[]string number bool list for as yeet "
        + "collect with if split join sort"
    )
    tokens: Final = _tokenize_source(source)

    # Add 1 because we have two different keywords for boolean literals (`true` and `false`),
    # so they map to 2 tokens but share one TokenType.
    assert len(tokens) == len(TokenType) + 1
    assert tokens[0].type == TokenType.SEMICOLON
    assert tokens[0].source_location == SourceLocation(source, offset=0, length=1)
    assert tokens[0].source_location.lexeme == ";"

    assert tokens[1].type == TokenType.EQUALS
    assert tokens[1].source_location == SourceLocation(source, offset=1, length=1)
    assert tokens[1].source_location.lexeme == "="

    assert tokens[2].type == TokenType.PLUS
    assert tokens[2].source_location == SourceLocation(source, offset=2, length=1)
    assert tokens[2].source_location.lexeme == "+"

    assert tokens[3].type == TokenType.MINUS
    assert tokens[3].source_location == SourceLocation(source, offset=3, length=1)
    assert tokens[3].source_location.lexeme == "-"

    assert tokens[4].type == TokenType.ASTERISK
    assert tokens[4].source_location == SourceLocation(source, offset=4, length=1)
    assert tokens[4].source_location.lexeme == "*"

    assert tokens[5].type == TokenType.PERCENT
    assert tokens[5].source_location == SourceLocation(source, offset=5, length=1)
    assert tokens[5].source_location.lexeme == "%"

    assert tokens[6].type == TokenType.SLASH
    assert tokens[6].source_location == SourceLocation(source, offset=6, length=1)
    assert tokens[6].source_location.lexeme == "/"

    assert tokens[7].type == TokenType.LEFT_PARENTHESIS
    assert tokens[7].source_location == SourceLocation(source, offset=7, length=1)
    assert tokens[7].source_location.lexeme == "("

    assert tokens[8].type == TokenType.RIGHT_PARENTHESIS
    assert tokens[8].source_location == SourceLocation(source, offset=8, length=1)
    assert tokens[8].source_location.lexeme == ")"

    assert tokens[9].type == TokenType.STORE
    assert tokens[9].source_location == SourceLocation(source, offset=9, length=5)
    assert tokens[9].source_location.lexeme == "STORE"

    assert tokens[10].type == TokenType.PRINT
    assert tokens[10].source_location == SourceLocation(source, offset=15, length=5)
    assert tokens[10].source_location.lexeme == "PRINT"

    assert tokens[11].type == TokenType.IDENTIFIER
    assert tokens[11].source_location == SourceLocation(source, offset=21, length=19)
    assert tokens[11].source_location.lexeme == "some_identifier_123"

    assert tokens[12].type == TokenType.STRING_LITERAL
    assert tokens[12].source_location == SourceLocation(source, offset=41, length=44)
    assert tokens[12].source_location.lexeme == r"'my string 🐍\'quoted\'\ntext on second line'"

    assert tokens[13].type == TokenType.NUMBER_LITERAL
    assert tokens[13].source_location == SourceLocation(source, offset=86, length=4)
    assert tokens[13].source_location.lexeme == "3.14"

    assert tokens[14].type == TokenType.LET
    assert tokens[14].source_location == SourceLocation(source, offset=91, length=3)
    assert tokens[14].source_location.lexeme == "LET"

    assert tokens[15].type == TokenType.PARAMS
    assert tokens[15].source_location == SourceLocation(source, offset=95, length=6)
    assert tokens[15].source_location.lexeme == "PARAMS"

    assert tokens[16].type == TokenType.COMMA
    assert tokens[16].source_location == SourceLocation(source, offset=101, length=1)
    assert tokens[16].source_location.lexeme == ","

    assert tokens[17].type == TokenType.DOLLAR
    assert tokens[17].source_location == SourceLocation(source, offset=102, length=1)
    assert tokens[17].source_location.lexeme == "$"

    assert tokens[18].type == TokenType.EXCLAMATION_MARK
    assert tokens[18].source_location == SourceLocation(source, offset=103, length=1)
    assert tokens[18].source_location.lexeme == "!"

    assert tokens[19].type == TokenType.COLON
    assert tokens[19].source_location == SourceLocation(source, offset=104, length=1)
    assert tokens[19].source_location.lexeme == ":"

    assert tokens[20].type == TokenType.QUESTION_MARK
    assert tokens[20].source_location == SourceLocation(source, offset=105, length=1)
    assert tokens[20].source_location.lexeme == "?"

    assert tokens[21].type == TokenType.BOOL_LITERAL
    assert tokens[21].source_location == SourceLocation(source, offset=106, length=4)
    assert tokens[21].source_location.lexeme == "true"

    assert tokens[22].type == TokenType.BOOL_LITERAL
    assert tokens[22].source_location == SourceLocation(source, offset=111, length=5)
    assert tokens[22].source_location.lexeme == "false"

    assert tokens[23].type == TokenType.EQUALS_EQUALS
    assert tokens[23].source_location == SourceLocation(source, offset=116, length=2)
    assert tokens[23].source_location.lexeme == "=="

    assert tokens[24].type == TokenType.EXCLAMATION_MARK_EQUALS
    assert tokens[24].source_location == SourceLocation(source, offset=119, length=2)
    assert tokens[24].source_location.lexeme == "!="

    assert tokens[25].type == TokenType.LESS_THAN
    assert tokens[25].source_location == SourceLocation(source, offset=122, length=1)
    assert tokens[25].source_location.lexeme == "<"

    assert tokens[26].type == TokenType.LESS_THAN_EQUALS
    assert tokens[26].source_location == SourceLocation(source, offset=124, length=2)
    assert tokens[26].source_location.lexeme == "<="

    assert tokens[27].type == TokenType.GREATER_THAN
    assert tokens[27].source_location == SourceLocation(source, offset=127, length=1)
    assert tokens[27].source_location.lexeme == ">"

    assert tokens[28].type == TokenType.GREATER_THAN_EQUALS
    assert tokens[28].source_location == SourceLocation(source, offset=129, length=2)
    assert tokens[28].source_location.lexeme == ">="

    assert tokens[29].type == TokenType.DOT_DOT_EQUALS
    assert tokens[29].source_location == SourceLocation(source, offset=132, length=3)
    assert tokens[29].source_location.lexeme == "..="

    assert tokens[30].type == TokenType.DOT_DOT_LESS_THAN
    assert tokens[30].source_location == SourceLocation(source, offset=136, length=3)
    assert tokens[30].source_location.lexeme == "..<"

    assert tokens[31].type == TokenType.AND
    assert tokens[31].source_location == SourceLocation(source, offset=140, length=3)
    assert tokens[31].source_location.lexeme == "and"

    assert tokens[32].type == TokenType.OR
    assert tokens[32].source_location == SourceLocation(source, offset=144, length=2)
    assert tokens[32].source_location.lexeme == "or"

    assert tokens[33].type == TokenType.NOT
    assert tokens[33].source_location == SourceLocation(source, offset=147, length=3)
    assert tokens[33].source_location.lexeme == "not"

    assert tokens[34].type == TokenType.HASH
    assert tokens[34].source_location == SourceLocation(source, offset=150, length=1)
    assert tokens[34].source_location.lexeme == "#"

    assert tokens[35].type == TokenType.LEFT_SQUARE_BRACKET
    assert tokens[35].source_location == SourceLocation(source, offset=151, length=1)
    assert tokens[35].source_location.lexeme == "["

    assert tokens[36].type == TokenType.RIGHT_SQUARE_BRACKET
    assert tokens[36].source_location == SourceLocation(source, offset=152, length=1)
    assert tokens[36].source_location.lexeme == "]"

    assert tokens[37].type == TokenType.STRING
    assert tokens[37].source_location == SourceLocation(source, offset=153, length=6)
    assert tokens[37].source_location.lexeme == "string"

    assert tokens[38].type == TokenType.NUMBER
    assert tokens[38].source_location == SourceLocation(source, offset=160, length=6)
    assert tokens[38].source_location.lexeme == "number"

    assert tokens[39].type == TokenType.BOOL
    assert tokens[39].source_location == SourceLocation(source, offset=167, length=4)
    assert tokens[39].source_location.lexeme == "bool"

    assert tokens[40].type == TokenType.LIST
    assert tokens[40].source_location == SourceLocation(source, offset=172, length=4)
    assert tokens[40].source_location.lexeme == "list"

    assert tokens[41].type == TokenType.FOR
    assert tokens[41].source_location == SourceLocation(source, offset=177, length=3)
    assert tokens[41].source_location.lexeme == "for"

    assert tokens[42].type == TokenType.AS
    assert tokens[42].source_location == SourceLocation(source, offset=181, length=2)
    assert tokens[42].source_location.lexeme == "as"

    assert tokens[43].type == TokenType.YEET
    assert tokens[43].source_location == SourceLocation(source, offset=184, length=4)
    assert tokens[43].source_location.lexeme == "yeet"

    assert tokens[44].type == TokenType.COLLECT
    assert tokens[44].source_location == SourceLocation(source, offset=189, length=7)
    assert tokens[44].source_location.lexeme == "collect"

    assert tokens[45].type == TokenType.WITH
    assert tokens[45].source_location == SourceLocation(source, offset=197, length=4)
    assert tokens[45].source_location.lexeme == "with"

    assert tokens[46].type == TokenType.IF
    assert tokens[46].source_location == SourceLocation(source, offset=202, length=2)
    assert tokens[46].source_location.lexeme == "if"

    assert tokens[47].type == TokenType.SPLIT
    assert tokens[47].source_location == SourceLocation(source, offset=205, length=5)
    assert tokens[47].source_location.lexeme == "split"

    assert tokens[48].type == TokenType.JOIN
    assert tokens[48].source_location == SourceLocation(source, offset=211, length=4)
    assert tokens[48].source_location.lexeme == "join"

    assert tokens[49].type == TokenType.SORT
    assert tokens[49].source_location == SourceLocation(source, offset=216, length=4)
    assert tokens[49].source_location.lexeme == "sort"

    assert tokens[50].type == TokenType.END_OF_INPUT
    assert tokens[50].source_location == SourceLocation(source, offset=220, length=1)
    assert tokens[50].source_location.lexeme == ""


def test_invalid_escape_sequence_raises() -> None:
    source: Final = r"'\x'"
    lexer: Final = Lexer(source)
    with pytest.raises(LexerError) as exception_info:
        lexer.tokenize()
    error: Final = exception_info.value
    assert r"Invalid escape sequence '\x'." in str(error)
    # Error points at the escaped character.
    assert error.source_location == SourceLocation(source, offset=2, length=1)


def test_unterminated_string_literal_raises() -> None:
    source: Final = "'no end"
    lexer: Final = Lexer(source)
    with pytest.raises(LexerError) as exception_info:
        lexer.tokenize()
    error: Final = exception_info.value
    assert "Unterminated string literal." in str(error)
    # Error source location should point to end of input.
    assert error.source_location == SourceLocation(source, offset=len(source), length=1)


def test_invalid_number_format_trailing_dot_raises() -> None:
    source: Final = "123."
    lexer: Final = Lexer(source)
    with pytest.raises(LexerError) as exception_info:
        lexer.tokenize()
    error: Final = exception_info.value
    assert "Invalid number format at offset." in str(error)
    assert error.source_location == SourceLocation(source, offset=len(source), length=1)


def test_tokenizing_integer_number_succeeds() -> None:
    source: Final = "42"
    tokens: Final = _tokenize_source(source)
    assert len(tokens) == 2  # Number literal + end of input.
    assert tokens[0].type == TokenType.NUMBER_LITERAL
    assert tokens[0].source_location == SourceLocation(source, offset=0, length=2)
    assert tokens[0].source_location.lexeme == "42"

    assert tokens[1].type == TokenType.END_OF_INPUT
    assert tokens[1].source_location == SourceLocation(source, offset=2, length=1)
    assert tokens[1].source_location.lexeme == ""


def test_invalid_non_ascii_character_raises() -> None:
    source: Final = "🐍"
    lexer: Final = Lexer(source)
    with pytest.raises(LexerError) as exception_info:
        lexer.tokenize()
    error: Final = exception_info.value
    assert "Invalid character '🐍'." in str(error)
    assert error.source_location == SourceLocation(source, offset=0, length=1)


def test_unexpected_underscore_start_raises() -> None:
    source: Final = "_"
    lexer: Final = Lexer(source)
    with pytest.raises(LexerError) as exception_info:
        lexer.tokenize()
    error: Final = exception_info.value
    assert "Unexpected character '_'" in str(error)
    assert error.source_location == SourceLocation(source, offset=0, length=1)


def test_advance_returns_sentinel_at_end() -> None:
    source: Final = ""
    lexer: Final = Lexer(source)
    # Calling advance when at end should return the sentinel character.
    first_result: Final = lexer._advance()  # type: ignore[reportPrivateUsage]
    assert first_result == "\0"
    # Subsequent advances should keep returning the sentinel character.
    second_result: Final = lexer._advance()  # type: ignore[reportPrivateUsage]
    assert second_result == "\0"
