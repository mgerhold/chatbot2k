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
        r";=+-*/()STORE PRINT some_identifier_123 'my string 🐍\'quoted\'\ntext on second line' 3.14 LET PARAMS,"
    )
    tokens: Final = _tokenize_source(source)
    assert len(tokens) == len(TokenType)
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

    assert tokens[5].type == TokenType.SLASH
    assert tokens[5].source_location == SourceLocation(source, offset=5, length=1)
    assert tokens[5].source_location.lexeme == "/"

    assert tokens[6].type == TokenType.LEFT_PARENTHESIS
    assert tokens[6].source_location == SourceLocation(source, offset=6, length=1)
    assert tokens[6].source_location.lexeme == "("

    assert tokens[7].type == TokenType.RIGHT_PARENTHESIS
    assert tokens[7].source_location == SourceLocation(source, offset=7, length=1)
    assert tokens[7].source_location.lexeme == ")"

    assert tokens[8].type == TokenType.STORE
    assert tokens[8].source_location == SourceLocation(source, offset=8, length=5)
    assert tokens[8].source_location.lexeme == "STORE"

    assert tokens[9].type == TokenType.PRINT
    assert tokens[9].source_location == SourceLocation(source, offset=14, length=5)
    assert tokens[9].source_location.lexeme == "PRINT"

    assert tokens[10].type == TokenType.IDENTIFIER
    assert tokens[10].source_location == SourceLocation(source, offset=20, length=19)
    assert tokens[10].source_location.lexeme == "some_identifier_123"

    assert tokens[11].type == TokenType.STRING_LITERAL
    assert tokens[11].source_location == SourceLocation(source, offset=40, length=44)
    assert tokens[11].source_location.lexeme == r"'my string 🐍\'quoted\'\ntext on second line'"

    assert tokens[12].type == TokenType.NUMBER_LITERAL
    assert tokens[12].source_location == SourceLocation(source, offset=85, length=4)
    assert tokens[12].source_location.lexeme == "3.14"

    assert tokens[13].type == TokenType.LET
    assert tokens[13].source_location == SourceLocation(source, offset=90, length=3)
    assert tokens[13].source_location.lexeme == "LET"

    assert tokens[14].type == TokenType.PARAMS
    assert tokens[14].source_location == SourceLocation(source, offset=94, length=6)
    assert tokens[14].source_location.lexeme == "PARAMS"

    assert tokens[15].type == TokenType.COMMA
    assert tokens[15].source_location == SourceLocation(source, offset=100, length=1)
    assert tokens[15].source_location.lexeme == ","

    assert tokens[16].type == TokenType.END_OF_INPUT
    assert tokens[16].source_location == SourceLocation(source, offset=101, length=1)
    assert tokens[16].source_location.lexeme == ""


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
