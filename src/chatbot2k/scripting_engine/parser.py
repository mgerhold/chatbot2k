from collections.abc import Callable
from typing import Annotated
from typing import Final
from typing import NamedTuple
from typing import Optional
from typing import final

from chatbot2k.scripting_engine.precedence import Precedence
from chatbot2k.scripting_engine.token import Token
from chatbot2k.scripting_engine.token_types import TokenType
from chatbot2k.scripting_engine.types.ast import Script
from chatbot2k.scripting_engine.types.ast import Store
from chatbot2k.scripting_engine.types.expressions import BinaryOperationExpression
from chatbot2k.scripting_engine.types.expressions import BinaryOperator
from chatbot2k.scripting_engine.types.expressions import Expression
from chatbot2k.scripting_engine.types.expressions import NumberLiteralExpression
from chatbot2k.scripting_engine.types.expressions import StoreIdentifierExpression
from chatbot2k.scripting_engine.types.expressions import StringLiteralExpression
from chatbot2k.scripting_engine.types.expressions import UnaryOperationExpression
from chatbot2k.scripting_engine.types.expressions import UnaryOperator
from chatbot2k.scripting_engine.types.expressions import VariableIdentifierExpression
from chatbot2k.scripting_engine.types.statements import AssignmentStatement
from chatbot2k.scripting_engine.types.statements import PrintStatement
from chatbot2k.scripting_engine.types.statements import Statement
from chatbot2k.scripting_engine.types.statements import VariableDefinitionStatement


@final
class ExpectedTokenError(RuntimeError):
    def __init__(self, token: Token, message: str) -> None:
        start_position: Final = token.source_location.range.start
        super().__init__(f"Expected {message} at line {start_position.line}, column {start_position.column}.")


@final
class StoreRedefinitionError(RuntimeError):
    def __init__(self, store_name: str) -> None:
        super().__init__(f"Store '{store_name}' is already defined.")


@final
class VariableRedefinitionError(RuntimeError):
    def __init__(self, variable_name: str) -> None:
        super().__init__(f"Variable '{variable_name}' is already defined.")


@final
class UnknownVariableError(RuntimeError):
    def __init__(self, variable_name: str) -> None:
        super().__init__(f"Variable '{variable_name}' is not defined.")


type _UnaryParser = Callable[
    [
        Parser,
        list[Store],
        list[VariableDefinitionStatement],
    ],
    Expression,
]
type _BinaryParser = Callable[
    [
        Parser,
        Annotated[Expression, "left operand"],
        list[Store],
        list[VariableDefinitionStatement],
    ],
    Expression,
]


@final
class _TableEntry(NamedTuple):
    prefix_parser: Optional[_UnaryParser]
    infix_parser: Optional[_BinaryParser]
    infix_precedence: Precedence


@final
class Parser:
    def __init__(self, script_name: str, tokens: list[Token]) -> None:
        self._script_name: Final = script_name
        self._tokens: Final = tokens
        self._current_index = 0

    def parse(self) -> Script:
        stores: Final = self._stores()
        statements: Final = self._statements(stores)
        return Script(
            name=self._script_name,
            stores=stores,
            statements=statements,
        )

    def _stores(self) -> list[Store]:
        stores: Final[list[Store]] = []
        while self._match(TokenType.STORE) is not None:
            stores.append(self._store(stores))
        return stores

    def _store(self, stores: list[Store]) -> Store:
        store_name: Final = self._expect(TokenType.IDENTIFIER, "store name").source_location.lexeme
        previous_definition: Final = next(
            (store for store in stores if store.name == store_name),
            None,
        )
        if previous_definition is not None:
            raise StoreRedefinitionError(store_name)
        self._expect(TokenType.EQUALS, "'=' after store name")
        store: Optional[Store] = None
        if (number_token := self._match(TokenType.NUMBER_LITERAL)) is not None:
            store = Store(
                name=store_name,
                value=NumberLiteralExpression(value=float(number_token.source_location.lexeme)),
            )
        if (string_token := self._match(TokenType.STRING_LITERAL)) is not None:
            store = Store(
                name=store_name,
                value=StringLiteralExpression.from_lexeme(string_token.source_location.lexeme),
            )
        if store is None:
            raise ExpectedTokenError(self._current(), "initial store value")
        self._expect(TokenType.SEMICOLON, "';' after store declaration")
        return store

    def _statements(self, stores: list[Store]) -> list[Statement]:
        statements: Final[list[Statement]] = []
        # The following list is only used internally to keep track of variable definitions
        # that already happened. It is not part of the returned Script. Using this list,
        # the parser does a simple semantic check to prevent re-defining variables and
        # to ensure variables are defined before use. This is not a clear separation
        # of concerns, but we don't want to add a separate semantic analysis phase.
        variable_definitions: Final[list[VariableDefinitionStatement]] = []
        while not self._is_at_end():
            statements.append(self._statement(stores, variable_definitions))
        if not statements:
            raise ExpectedTokenError(self._current(), "at least one statement")
        return statements

    def _statement(
        self,
        stores: list[Store],
        variable_definitions: list[VariableDefinitionStatement],
    ) -> Statement:
        statement: Statement
        match self._current().type:
            case TokenType.PRINT:
                statement = self._print_statement(stores, variable_definitions)
            case TokenType.IDENTIFIER:
                statement = self._assignment(stores, variable_definitions)
            case TokenType.LET:
                statement = self._variable_definition(stores, variable_definitions)
            case _:
                raise ExpectedTokenError(self._current(), "statement")
        self._expect(TokenType.SEMICOLON, "';' after statement")
        return statement

    def _print_statement(
        self,
        stores: list[Store],
        variable_definitions: list[VariableDefinitionStatement],
    ) -> Statement:
        self._expect(TokenType.PRINT, "'print' keyword")  # This is a double-check.
        expression: Final = self._expression(stores, variable_definitions, Precedence.UNKNOWN)
        return PrintStatement(argument=expression)

    def _assignment(
        self,
        stores: list[Store],
        variable_definitions: list[VariableDefinitionStatement],
    ) -> Statement:
        identifier_token: Final = self._expect(TokenType.IDENTIFIER, "assignment target")
        identifier_name: Final = identifier_token.source_location.lexeme

        # Check if it's a store
        store: Final = next((store for store in stores if store.name == identifier_name), None)
        if store is not None:
            lvalue: StoreIdentifierExpression | VariableIdentifierExpression = StoreIdentifierExpression(
                store_name=identifier_name,
                data_type=store.data_type,
            )
        else:
            # Check if it's a variable
            variable: Final = next(
                (var for var in variable_definitions if var.variable_name == identifier_name),
                None,
            )
            if variable is None:
                raise UnknownVariableError(identifier_name)
            lvalue = VariableIdentifierExpression(
                variable_name=identifier_name,
                data_type=variable.data_type,
            )

        self._expect(TokenType.EQUALS, "'=' in assignment")
        rvalue: Final = self._expression(stores, variable_definitions, Precedence.UNKNOWN)
        return AssignmentStatement(
            assignment_target=lvalue,
            expression=rvalue,
        )

    def _variable_definition(
        self,
        stores: list[Store],
        variable_definitions: list[VariableDefinitionStatement],
    ) -> Statement:
        self._expect(TokenType.LET, "'let' keyword")  # This is a double-check.
        identifier_token: Final = self._expect(TokenType.IDENTIFIER, "variable name")
        identifier_name: Final = identifier_token.source_location.lexeme
        previous_definition: Final = next(
            (definition for definition in variable_definitions if definition.variable_name == identifier_name),
            None,
        )
        if previous_definition is not None:
            raise VariableRedefinitionError(identifier_name)
        self._expect(TokenType.EQUALS, "'=' in variable definition")
        initial_value: Final = self._expression(
            stores,
            variable_definitions,
            Precedence.UNKNOWN,
        )
        definition: Final = VariableDefinitionStatement(
            variable_name=identifier_name,
            data_type=initial_value.get_data_type(),
            initial_value=initial_value,
        )
        variable_definitions.append(definition)
        return definition

    def _expression(
        self,
        stores: list[Store],
        variable_definitions: list[VariableDefinitionStatement],
        precedence: Precedence,
    ) -> Expression:
        table_entry = Parser._PARSER_TABLE[self._current().type]
        prefix_parser: Final = table_entry.prefix_parser
        if prefix_parser is None:
            raise ExpectedTokenError(self._current(), "expression")
        left_operand = prefix_parser(self, stores, variable_definitions)

        while True:
            table_entry = Parser._PARSER_TABLE[self._current().type]
            if table_entry.infix_precedence <= precedence or table_entry.infix_parser is None:
                return left_operand
            left_operand = table_entry.infix_parser(self, left_operand, stores, variable_definitions)

    def _identifier(
        self,
        stores: list[Store],
        variable_definitions: list[VariableDefinitionStatement],
    ) -> Expression:
        identifier_token: Final = self._expect(TokenType.IDENTIFIER, "identifier")  # This is a double-check.
        store: Final = next(
            (store for store in stores if store.name == identifier_token.source_location.lexeme),
            None,
        )
        if store is not None:
            return StoreIdentifierExpression(
                store_name=store.name,
                data_type=store.data_type,
            )
        variable_definition: Final = next(
            (
                definition
                for definition in variable_definitions
                if definition.variable_name == identifier_token.source_location.lexeme
            ),
            None,
        )
        if variable_definition is not None:
            return VariableIdentifierExpression(
                variable_name=variable_definition.variable_name,
                data_type=variable_definition.data_type,
            )
        raise UnknownVariableError(identifier_token.source_location.lexeme)

    def _number_literal(
        self,
        _stores: list[Store],
        _variable_definitions: list[VariableDefinitionStatement],
    ) -> Expression:
        number_token: Final = self._expect(TokenType.NUMBER_LITERAL, "number literal")  # This is a double-check.
        return NumberLiteralExpression(value=float(number_token.source_location.lexeme))

    def _string_literal(
        self,
        _stores: list[Store],
        _variable_definitions: list[VariableDefinitionStatement],
    ) -> Expression:
        string_token: Final = self._expect(TokenType.STRING_LITERAL, "string literal")  # This is a double-check.
        return StringLiteralExpression.from_lexeme(string_token.source_location.lexeme)

    def _unary_operation(
        self,
        stores: list[Store],
        variable_definitions: list[VariableDefinitionStatement],
    ) -> Expression:
        unary_operator: UnaryOperator
        match self._current().type:
            case TokenType.PLUS:
                unary_operator = UnaryOperator.PLUS
            case TokenType.MINUS:
                unary_operator = UnaryOperator.NEGATE
            case _:
                msg: Final = f"unexpected unary operator: {self._current().type}"
                raise AssertionError(msg)
        self._advance()
        operand: Final = self._expression(stores, variable_definitions, Precedence.UNARY)
        return UnaryOperationExpression(operator=unary_operator, operand=operand)

    def _grouped_expression(
        self,
        stores: list[Store],
        variable_definitions: list[VariableDefinitionStatement],
    ) -> Expression:
        self._expect(TokenType.LEFT_PARENTHESIS, "'('")  # This is a double-check.
        expression: Final = self._expression(stores, variable_definitions, Precedence.UNKNOWN)
        self._expect(TokenType.RIGHT_PARENTHESIS, "')' after grouped expression")
        return expression

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

    def _binary_expression(
        self,
        left_operand: Expression,
        stores: list[Store],
        variable_definitions: list[VariableDefinitionStatement],
    ) -> Expression:
        binary_operator: BinaryOperator
        match self._current().type:
            case TokenType.PLUS:
                binary_operator = BinaryOperator.ADD
            case TokenType.MINUS:
                binary_operator = BinaryOperator.SUBTRACT
            case TokenType.ASTERISK:
                binary_operator = BinaryOperator.MULTIPLY
            case TokenType.SLASH:
                binary_operator = BinaryOperator.DIVIDE
            case _:
                msg = f"unexpected binary operator: {self._current().type}"
                raise AssertionError(msg)
        precedence: Final = Parser._PARSER_TABLE[self._current().type].infix_precedence
        self._advance()
        right_operand: Final = self._expression(stores, variable_definitions, precedence)
        return BinaryOperationExpression(left=left_operand, operator=binary_operator, right=right_operand)

    _PARSER_TABLE = {
        TokenType.SEMICOLON: _TableEntry(None, None, Precedence.UNKNOWN),
        TokenType.EQUALS: _TableEntry(None, None, Precedence.UNKNOWN),
        TokenType.PLUS: _TableEntry(_unary_operation, _binary_expression, Precedence.SUM),
        TokenType.MINUS: _TableEntry(_unary_operation, _binary_expression, Precedence.SUM),
        TokenType.ASTERISK: _TableEntry(None, _binary_expression, Precedence.PRODUCT),
        TokenType.SLASH: _TableEntry(None, _binary_expression, Precedence.PRODUCT),
        TokenType.LEFT_PARENTHESIS: _TableEntry(_grouped_expression, None, Precedence.UNKNOWN),
        TokenType.RIGHT_PARENTHESIS: _TableEntry(None, None, Precedence.UNKNOWN),
        TokenType.STORE: _TableEntry(None, None, Precedence.UNKNOWN),
        TokenType.PRINT: _TableEntry(None, None, Precedence.UNKNOWN),
        TokenType.LET: _TableEntry(None, None, Precedence.UNKNOWN),
        TokenType.IDENTIFIER: _TableEntry(_identifier, None, Precedence.UNARY),
        TokenType.STRING_LITERAL: _TableEntry(_string_literal, None, Precedence.UNARY),
        TokenType.NUMBER_LITERAL: _TableEntry(_number_literal, None, Precedence.UNARY),
        TokenType.END_OF_INPUT: _TableEntry(None, None, Precedence.UNKNOWN),
    }
