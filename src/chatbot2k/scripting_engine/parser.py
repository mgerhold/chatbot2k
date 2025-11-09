from typing import Final
from typing import Optional
from typing import final

from chatbot2k.scripting_engine.token import Token
from chatbot2k.scripting_engine.token_types import TokenType
from chatbot2k.scripting_engine.types import AssignmentStatement
from chatbot2k.scripting_engine.types import Expression
from chatbot2k.scripting_engine.types import NumberLiteralExpression
from chatbot2k.scripting_engine.types import NumberValue
from chatbot2k.scripting_engine.types import PrintStatement
from chatbot2k.scripting_engine.types import Script
from chatbot2k.scripting_engine.types import Statement
from chatbot2k.scripting_engine.types import Store
from chatbot2k.scripting_engine.types import StoreIdentifierExpression
from chatbot2k.scripting_engine.types import StringLiteralExpression
from chatbot2k.scripting_engine.types import StringValue
from chatbot2k.scripting_engine.types import VariableIdentifierExpression


@final
class ExpectedTokenError(RuntimeError):
    def __init__(self, token: Token, message: str) -> None:
        start_position: Final = token.source_location.range.start
        super().__init__(f"Expected {message} at line {start_position.line}, column {start_position.column}.")


@final
class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens: Final = tokens
        self._current_index = 0

    def parse(self) -> Script:
        stores: Final = self._stores()
        statements: Final = self._statements(stores)
        return Script(
            stores=stores,
            statements=statements,
        )

    def _stores(self) -> list[Store]:
        stores: Final[list[Store]] = []
        while self._match(TokenType.STORE) is not None:
            stores.append(self._store())
        return stores

    def _store(self) -> Store:
        store_name: Final = self._expect(TokenType.IDENTIFIER, "store name").source_location.lexeme
        self._expect(TokenType.EQUALS, "'=' after store name")
        store: Optional[Store] = None
        if (number_token := self._match(TokenType.NUMBER_LITERAL)) is not None:
            store = Store(
                name=store_name,
                value=NumberValue(value=float(number_token.source_location.lexeme)),
            )
        if (string_token := self._match(TokenType.STRING_LITERAL)) is not None:
            store = Store(
                name=store_name,
                value=StringValue.from_lexeme(string_token.source_location.lexeme),
            )
        if store is None:
            raise ExpectedTokenError(self._current(), "initial store value")
        self._expect(TokenType.SEMICOLON, "';' after store declaration")
        return store

    def _statements(self, stores: list[Store]) -> list[Statement]:
        statements: Final[list[Statement]] = []
        while not self._is_at_end():
            statements.append(self._statement(stores))
        if not statements:
            raise ExpectedTokenError(self._current(), "at least one statement")
        return statements

    def _statement(self, stores: list[Store]) -> Statement:
        statement: Statement
        match self._current().type:
            case TokenType.PRINT:
                statement = self._print_statement(stores)
            case TokenType.IDENTIFIER:
                statement = self._assignment(stores)
            case _:
                raise ExpectedTokenError(self._current(), "statement")
        self._expect(TokenType.SEMICOLON, "';' after statement")
        return statement

    def _print_statement(self, stores: list[Store]) -> Statement:
        self._expect(TokenType.PRINT, "'print' keyword")  # This is a double-check.
        expression: Final = self._expression(stores)
        return PrintStatement(argument=expression)

    def _assignment(self, stores: list[Store]) -> Statement:
        identifier_token: Final = self._expect(TokenType.IDENTIFIER, "assignment target")
        identifier_name: Final = identifier_token.source_location.lexeme
        store: Final = next((store for store in stores if store.name == identifier_name), None)
        if store is None:
            raise NotImplementedError("Local variables are not yet supported.")
        lvalue: StoreIdentifierExpression | VariableIdentifierExpression = StoreIdentifierExpression(
            store_name=identifier_name,
            data_type=store.value.data_type,
        )
        self._expect(TokenType.EQUALS, "'=' in assignment")
        rvalue: Final = self._expression(stores)
        return AssignmentStatement(
            assignment_target=lvalue,
            expression=rvalue,
        )

    def _expression(self, stores: list[Store]) -> Expression:
        if (number_token := self._match(TokenType.NUMBER_LITERAL)) is not None:
            return NumberLiteralExpression(value=float(number_token.source_location.lexeme))
        if (string_token := self._match(TokenType.STRING_LITERAL)) is not None:
            return StringLiteralExpression(value=StringValue.from_lexeme(string_token.source_location.lexeme).value)
        if (identifier_token := self._match(TokenType.IDENTIFIER)) is not None:
            identifier_name: Final = identifier_token.source_location.lexeme
            store: Final = next((store for store in stores if store.name == identifier_name), None)
            if store is None:
                raise NotImplementedError("Local variables are not yet supported.")
            return StoreIdentifierExpression(
                store_name=identifier_name,
                data_type=store.value.data_type,
            )
        raise ExpectedTokenError(self._current(), "expression")

    def _is_at_end(self) -> bool:
        return (
            self._current_index >= len(self._tokens) or self._tokens[self._current_index].type == TokenType.END_OF_INPUT
        )

    def _current(self) -> Token:
        return self._tokens[-1] if self._is_at_end() else self._tokens[self._current_index]

    def _advance(self) -> Token:
        result: Final = self._current()
        if not self._is_at_end():
            self._current_index += 1
        return result

    def _match(self, token_type: TokenType) -> Optional[Token]:
        if self._is_at_end() or self._current().type != token_type:
            return None
        return self._advance()

    def _expect(self, token_type: TokenType, error_message: str) -> Token:
        token: Final = self._match(token_type)
        if token is None:
            raise ExpectedTokenError(self._current(), error_message)
        return token
