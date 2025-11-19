from typing import Final
from typing import Optional
from typing import final

from chatbot2k.scripting_engine.escape_characters import ESCAPE_CHARACTERS
from chatbot2k.scripting_engine.source_location import SourceLocation
from chatbot2k.scripting_engine.token import Token
from chatbot2k.scripting_engine.token_types import TokenType

_BUILTIN_KEYWORDS = {
    "STORE": TokenType.STORE,
    "PARAMS": TokenType.PARAMS,
    "PRINT": TokenType.PRINT,
    "LET": TokenType.LET,
}

_SINGLE_CHAR_TOKENS = {
    ",": TokenType.COMMA,
    "!": TokenType.EXCLAMATION_MARK,
    "$": TokenType.DOLLAR,
    ";": TokenType.SEMICOLON,
    "=": TokenType.EQUALS,
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.ASTERISK,
    "/": TokenType.SLASH,
    "(": TokenType.LEFT_PARENTHESIS,
    ")": TokenType.RIGHT_PARENTHESIS,
}


@final
class LexerError(RuntimeError):
    def __init__(self, message: str, source_location: SourceLocation) -> None:
        super().__init__(message)
        self.source_location: Final = source_location


@final
class Lexer:
    def __init__(self, source: str) -> None:
        self._source: Final = source
        self._current_offset = 0

    def tokenize(self) -> list[Token]:
        tokens: Final[list[Token]] = []
        while not self._is_at_end():
            self._discard_whitespace()
            match self._current():
                case c if c in _SINGLE_CHAR_TOKENS:
                    self._advance()
                    tokens.append(self._create_token(_SINGLE_CHAR_TOKENS[c]))
                case _ as char if char.isdigit():
                    # Number literal (we don't differentiate between integers and floats).
                    start_offset = self._current_offset
                    self._advance()
                    while self._current().isdigit():
                        self._advance()
                    if self._current() == ".":
                        self._advance()
                        if not self._current().isdigit():
                            raise LexerError(
                                "Invalid number format at offset.",
                                self._current_source_location,
                            )
                        while self._current().isdigit():
                            self._advance()
                    tokens.append(self._create_token(TokenType.NUMBER_LITERAL, start_offset))
                case "'":
                    # String literal.
                    start_offset = self._current_offset
                    self._advance()
                    while True:
                        if self._current() == "\\":
                            self._advance()
                            escaped_char = ESCAPE_CHARACTERS.get(self._current())
                            if escaped_char is None:
                                msg = f"Invalid escape sequence '\\{self._current()}'."
                                raise LexerError(msg, self._current_source_location)
                            self._advance()
                            continue
                        if self._current() == "'":
                            break
                        if self._is_at_end():
                            raise LexerError(
                                "Unterminated string literal.",
                                self._current_source_location,
                            )
                        self._advance()
                    self._advance()  # Consume closing quote.
                    tokens.append(self._create_token(TokenType.STRING_LITERAL, start_offset))
                case _ as char if Lexer._is_valid_identifier_start(char):
                    # Builtin keyword or identifier.
                    start_offset = self._current_offset
                    self._advance()
                    while Lexer._is_valid_identifier_continuation(self._current()):
                        self._advance()
                    lexeme = self._source[start_offset : self._current_offset]
                    builtin_keyword = _BUILTIN_KEYWORDS.get(lexeme)
                    if builtin_keyword is not None:
                        tokens.append(self._create_token(builtin_keyword, start_offset))
                    else:
                        tokens.append(self._create_token(TokenType.IDENTIFIER, start_offset))
                case _ as char if not char.isascii():
                    msg = f"Invalid character '{char}'."
                    raise LexerError(msg, self._current_source_location)
                case _:
                    msg = f"Unexpected character '{self._current()}'."
                    raise LexerError(msg, self._current_source_location)
        tokens.append(
            Token(
                type=TokenType.END_OF_INPUT,
                source_location=self._current_source_location,
            )
        )
        return tokens

    @staticmethod
    def _is_valid_identifier_start(char: str) -> bool:
        return char.isascii() and char.isalpha()

    @staticmethod
    def _is_valid_identifier_continuation(char: str) -> bool:
        return Lexer._is_valid_identifier_start(char) or char.isdigit() or char == "_"

    @property
    def _current_source_location(self) -> SourceLocation:
        return SourceLocation(
            source=self._source,
            offset=self._current_offset,
            length=1,
        )

    def _create_token(self, type_: TokenType, start_offset: Optional[int] = None) -> Token:
        if start_offset is None:
            start_offset = self._current_offset - 1
        return Token(
            type=type_,
            source_location=SourceLocation(
                source=self._source,
                offset=start_offset,
                length=self._current_offset - start_offset,
            ),
        )

    def _discard_whitespace(self) -> None:
        while self._current().isspace():
            self._advance()

    def _is_at_end(self) -> bool:
        return self._current_offset >= len(self._source)

    def _current(self) -> str:
        return "\0" if self._is_at_end() else self._source[self._current_offset]

    def _advance(self) -> str:
        result: Final = self._current()
        if self._is_at_end():
            return result
        self._current_offset += 1
        return result
