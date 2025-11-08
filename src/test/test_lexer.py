from typing import Final

from chatbot2k.scripting_engine.lexer import Lexer
from chatbot2k.scripting_engine.source_location import SourceLocation
from chatbot2k.scripting_engine.token import Token
from chatbot2k.scripting_engine.token_types import TokenType


def _tokenize_source(source: str) -> list[Token]:
    lexer: Final = Lexer(source)
    return lexer.tokenize()


def test_tokenize_can_analyze_all_token_types() -> None:
    source: Final = r";=+-*/STORE PRINT some_identifier_123 'my string 🐍\'quoted\'\ntext on second line' 3.14"
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

    assert tokens[6].type == TokenType.STORE
    assert tokens[6].source_location == SourceLocation(source, offset=6, length=5)
    assert tokens[6].source_location.lexeme == "STORE"

    assert tokens[7].type == TokenType.PRINT
    assert tokens[7].source_location == SourceLocation(source, offset=12, length=5)
    assert tokens[7].source_location.lexeme == "PRINT"

    assert tokens[8].type == TokenType.IDENTIFIER
    assert tokens[8].source_location == SourceLocation(source, offset=18, length=19)
    assert tokens[8].source_location.lexeme == "some_identifier_123"

    assert tokens[9].type == TokenType.STRING_LITERAL
    assert tokens[9].source_location == SourceLocation(source, offset=38, length=44)
    assert tokens[9].source_location.lexeme == r"'my string 🐍\'quoted\'\ntext on second line'"

    assert tokens[10].type == TokenType.NUMBER_LITERAL
    assert tokens[10].source_location == SourceLocation(source, offset=83, length=4)
    assert tokens[10].source_location.lexeme == "3.14"

    assert tokens[11].type == TokenType.END_OF_INPUT
    assert tokens[11].source_location == SourceLocation(source, offset=87, length=1)
    assert tokens[11].source_location.lexeme == ""
