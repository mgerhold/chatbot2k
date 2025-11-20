from collections.abc import Callable
from functools import lru_cache
from typing import Annotated
from typing import Final
from typing import NamedTuple
from typing import Optional
from typing import Self
from typing import final

from chatbot2k.scripting_engine.precedence import Precedence
from chatbot2k.scripting_engine.token import Token
from chatbot2k.scripting_engine.token_types import TokenType
from chatbot2k.scripting_engine.types.ast import Parameter
from chatbot2k.scripting_engine.types.ast import Script
from chatbot2k.scripting_engine.types.ast import Store
from chatbot2k.scripting_engine.types.data_types import DataType
from chatbot2k.scripting_engine.types.expressions import BinaryOperationExpression
from chatbot2k.scripting_engine.types.expressions import BinaryOperator
from chatbot2k.scripting_engine.types.expressions import BoolLiteralExpression
from chatbot2k.scripting_engine.types.expressions import Expression
from chatbot2k.scripting_engine.types.expressions import NumberLiteralExpression
from chatbot2k.scripting_engine.types.expressions import ParameterIdentifierExpression
from chatbot2k.scripting_engine.types.expressions import StoreIdentifierExpression
from chatbot2k.scripting_engine.types.expressions import StringLiteralExpression
from chatbot2k.scripting_engine.types.expressions import TernaryOperationExpression
from chatbot2k.scripting_engine.types.expressions import UnaryOperationExpression
from chatbot2k.scripting_engine.types.expressions import UnaryOperator
from chatbot2k.scripting_engine.types.expressions import VariableIdentifierExpression
from chatbot2k.scripting_engine.types.statements import AssignmentStatement
from chatbot2k.scripting_engine.types.statements import PrintStatement
from chatbot2k.scripting_engine.types.statements import Statement
from chatbot2k.scripting_engine.types.statements import VariableDefinitionStatement


class ParserError(RuntimeError): ...


@final
class ExpectedTokenError(ParserError):
    def __init__(self, token: Token, message: str) -> None:
        start_position: Final = token.source_location.range.start
        super().__init__(f"Expected {message} at line {start_position.line}, column {start_position.column}.")


@final
class StoreRedefinitionError(ParserError):
    def __init__(self, store_name: str) -> None:
        super().__init__(f"Store '{store_name}' is already defined.")


@final
class VariableRedefinitionError(ParserError):
    def __init__(self, variable_name: str) -> None:
        super().__init__(f"Variable '{variable_name}' is already defined.")


@final
class UnknownVariableError(ParserError):
    def __init__(self, variable_name: str) -> None:
        super().__init__(f"Variable '{variable_name}' is not defined.")


@final
class ParameterShadowsStoreError(ParserError):
    def __init__(self, parameter_name: str) -> None:
        super().__init__(f"Parameter '{parameter_name}' shadows store with the same name.")


@final
class VariableShadowsParameterError(ParserError):
    def __init__(self, variable_name: str) -> None:
        super().__init__(f"Variable '{variable_name}' shadows parameter with the same name.")


@final
class VariableShadowsStoreError(ParserError):
    def __init__(self, variable_name: str) -> None:
        super().__init__(f"Variable '{variable_name}' shadows store with the same name.")


@final
class DuplicateParameterNameError(ParserError):
    def __init__(self, parameter_name: str) -> None:
        super().__init__(f"Parameter '{parameter_name}' is already defined.")


@final
class TernaryConditionTypeError(ParserError):
    def __init__(self, condition_type: DataType) -> None:
        super().__init__(f"Ternary operator condition must be of type 'bool', got '{condition_type}'.")


@final
class TernaryOperatorTypeError(ParserError):
    def __init__(self, true_type: DataType, false_type: DataType) -> None:
        super().__init__(f"Ternary operator branches must have the same type, got '{true_type}' and '{false_type}'.")


@final
class ParserTypeError(ParserError):
    def __init__(self, invalid_type: DataType) -> None:
        super().__init__(f"Invalid type for operation: '{invalid_type}'.")


@final
class AssignmentTypeError(ParserError):
    def __init__(self, lvalue_type: DataType, rvalue_type: DataType) -> None:
        super().__init__(f"Cannot assign value of type '{rvalue_type}' to target of type '{lvalue_type}'.")


@final
class TypeNotCallableError(ParserError):
    def __init__(self, type_: DataType) -> None:
        super().__init__(f"Value of type '{type_}' is not callable.")


type _UnaryParser = Callable[
    [
        Parser,
        _ParseContext,
    ],
    Expression,
]
type _BinaryParser = Callable[
    [
        Parser,
        Annotated[Expression, "left operand"],
        _ParseContext,
    ],
    Expression,
]

_BINARY_OPERATOR_BY_TOKEN_TYPE = {
    # Arithmetic operators.
    TokenType.PLUS: BinaryOperator.ADD,
    TokenType.MINUS: BinaryOperator.SUBTRACT,
    TokenType.ASTERISK: BinaryOperator.MULTIPLY,
    TokenType.SLASH: BinaryOperator.DIVIDE,
    # Relational operators.
    TokenType.EQUALS_EQUALS: BinaryOperator.EQUALS,
    TokenType.EXCLAMATION_MARK_EQUALS: BinaryOperator.NOT_EQUALS,
    TokenType.LESS_THAN: BinaryOperator.LESS_THAN,
    TokenType.LESS_THAN_EQUALS: BinaryOperator.LESS_THAN_OR_EQUAL,
    TokenType.GREATER_THAN: BinaryOperator.GREATER_THAN,
    TokenType.GREATER_THAN_EQUALS: BinaryOperator.GREATER_THAN_OR_EQUAL,
    # Logical operators.
    TokenType.AND: BinaryOperator.AND,
    TokenType.OR: BinaryOperator.OR,
}


_UNARY_OPERATOR_BY_TOKEN_TYPE = {
    # Arithmetic operators.
    TokenType.PLUS: UnaryOperator.PLUS,
    TokenType.MINUS: UnaryOperator.NEGATE,
    # Logical operators.
    TokenType.NOT: UnaryOperator.NOT,
    # Miscellaneous operators.
    TokenType.DOLLAR: UnaryOperator.TO_NUMBER,
    TokenType.EXCLAMATION_MARK: UnaryOperator.EVALUATE,
    TokenType.HASH: UnaryOperator.TO_STRING,
}


@final
class _TableEntry(NamedTuple):
    prefix_parser: Optional[_UnaryParser]
    infix_parser: Optional[_BinaryParser]
    infix_precedence: Precedence

    @classmethod
    @lru_cache
    def unused(cls) -> Self:
        return cls(None, None, Precedence.UNKNOWN)


@final
class _ParseContext(NamedTuple):
    stores: list[Store]
    parameters: list[Parameter]
    variable_definitions: list[VariableDefinitionStatement]


@final
class Parser:
    def __init__(self, script_name: str, tokens: list[Token]) -> None:
        self._script_name: Final = script_name
        self._tokens: Final = tokens
        self._current_index = 0

    def parse(self) -> Script:
        stores: Final = self._stores()
        parameters: Final = self._parameters(stores)
        statements: Final = self._statements(stores, parameters)
        return Script(
            name=self._script_name,
            stores=stores,
            parameters=parameters,
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
        value: Final = self._expression(
            _ParseContext(
                stores=stores,
                parameters=[],
                variable_definitions=[],
            ),
            Precedence.UNKNOWN,
        )
        store: Final = Store(
            name=store_name,
            value=value,
        )
        self._expect(TokenType.SEMICOLON, "';' after store declaration")
        return store

    def _parameters(self, stores: list[Store]) -> list[Parameter]:
        if self._match(TokenType.PARAMS) is None:
            return []
        parameters: Final[list[Parameter]] = []
        while True:
            identifier_token = self._expect(TokenType.IDENTIFIER, "parameter name")
            parameter_name = identifier_token.source_location.lexeme
            if next((store.name for store in stores if store.name == parameter_name), None) is not None:
                raise ParameterShadowsStoreError(parameter_name)
            if next((parameter.name for parameter in parameters if parameter.name == parameter_name), None) is not None:
                raise DuplicateParameterNameError(parameter_name)
            parameter = Parameter(name=parameter_name)
            parameters.append(parameter)
            if self._match(TokenType.COMMA) is None or self._current().type == TokenType.SEMICOLON:
                break
        self._expect(TokenType.SEMICOLON, "';' after parameter list")
        return parameters

    def _statements(
        self,
        stores: list[Store],
        parameters: list[Parameter],
    ) -> list[Statement]:
        statements: Final[list[Statement]] = []
        # The following list is only used internally to keep track of variable definitions
        # that already happened. It is not part of the returned Script. Using this list,
        # the parser does a simple semantic check to prevent re-defining variables and
        # to ensure variables are defined before use. This is not a clear separation
        # of concerns, but we don't want to add a separate semantic analysis phase.
        variable_definitions: Final[list[VariableDefinitionStatement]] = []
        while not self._is_at_end():
            statements.append(self._statement(_ParseContext(stores, parameters, variable_definitions)))
        if not statements:
            raise ExpectedTokenError(self._current(), "at least one statement")
        return statements

    def _statement(
        self,
        environment: _ParseContext,
    ) -> Statement:
        statement: Statement
        match self._current().type:
            case TokenType.PRINT:
                statement = self._print_statement(environment)
            case TokenType.IDENTIFIER:
                statement = self._assignment(environment)
            case TokenType.LET:
                statement = self._variable_definition(environment)
            case _:
                raise ExpectedTokenError(self._current(), "statement")
        self._expect(TokenType.SEMICOLON, "';' after statement")
        return statement

    def _print_statement(
        self,
        context: _ParseContext,
    ) -> Statement:
        self._expect(TokenType.PRINT, "'print' keyword")  # This is a double-check.
        expression: Final = self._expression(context, Precedence.UNKNOWN)
        expression_type: Final = expression.get_data_type()
        if expression_type not in (DataType.NUMBER, DataType.STRING, DataType.BOOL):
            raise ParserTypeError(expression_type)
        return PrintStatement(argument=expression)

    def _assignment(
        self,
        context: _ParseContext,
    ) -> Statement:
        identifier_token: Final = self._expect(TokenType.IDENTIFIER, "assignment target")
        identifier_name: Final = identifier_token.source_location.lexeme

        # Check if it's a store.
        if (store := next((store for store in context.stores if store.name == identifier_name), None)) is not None:
            lvalue: StoreIdentifierExpression | ParameterIdentifierExpression | VariableIdentifierExpression = (
                StoreIdentifierExpression(
                    store_name=identifier_name,
                    data_type=store.data_type,
                )
            )
        # Check if it's a parameter.
        elif (
            next((parameter for parameter in context.parameters if parameter.name == identifier_name), None) is not None
        ):
            lvalue = ParameterIdentifierExpression(parameter_name=identifier_name)
        # Check if it's a variable.
        elif (
            variable := next(
                (var for var in context.variable_definitions if var.variable_name == identifier_name),
                None,
            )
        ) is not None:
            lvalue = VariableIdentifierExpression(
                variable_name=identifier_name,
                data_type=variable.data_type,
            )
        else:
            raise UnknownVariableError(identifier_name)

        self._expect(TokenType.EQUALS, "'=' in assignment")
        rvalue: Final = self._expression(context, Precedence.UNKNOWN)

        lvalue_type: Final = lvalue.get_data_type()
        rvalue_type: Final = rvalue.get_data_type()
        if lvalue_type != rvalue_type:
            raise AssignmentTypeError(lvalue_type, rvalue_type)

        return AssignmentStatement(
            assignment_target=lvalue,
            expression=rvalue,
        )

    def _variable_definition(
        self,
        context: _ParseContext,
    ) -> Statement:
        self._expect(TokenType.LET, "'let' keyword")  # This is a double-check.
        identifier_token: Final = self._expect(TokenType.IDENTIFIER, "variable name")
        identifier_name: Final = identifier_token.source_location.lexeme
        if next((store.name for store in context.stores if store.name == identifier_name), None) is not None:
            raise VariableShadowsStoreError(identifier_name)
        if (
            next((parameter.name for parameter in context.parameters if parameter.name == identifier_name), None)
            is not None
        ):
            raise VariableShadowsParameterError(identifier_name)
        previous_definition: Final = next(
            (definition for definition in context.variable_definitions if definition.variable_name == identifier_name),
            None,
        )
        if previous_definition is not None:
            raise VariableRedefinitionError(identifier_name)
        self._expect(TokenType.EQUALS, "'=' in variable definition")
        initial_value: Final = self._expression(
            context,
            Precedence.UNKNOWN,
        )
        definition: Final = VariableDefinitionStatement(
            variable_name=identifier_name,
            data_type=initial_value.get_data_type(),
            initial_value=initial_value,
        )
        context.variable_definitions.append(definition)
        return definition

    def _expression(
        self,
        context: _ParseContext,
        precedence: Precedence,
    ) -> Expression:
        table_entry = Parser._PARSER_TABLE[self._current().type]
        prefix_parser: Final = table_entry.prefix_parser
        if prefix_parser is None:
            raise ExpectedTokenError(self._current(), "expression")
        left_operand = prefix_parser(self, context)

        while True:
            table_entry = Parser._PARSER_TABLE[self._current().type]
            if table_entry.infix_precedence <= precedence or table_entry.infix_parser is None:
                return left_operand
            left_operand = table_entry.infix_parser(self, left_operand, context)

    def _identifier(
        self,
        context: _ParseContext,
    ) -> Expression:
        identifier_token: Final = self._expect(TokenType.IDENTIFIER, "identifier")  # This is a double-check.
        identifier_name: Final = identifier_token.source_location.lexeme
        store: Final = next(
            (store for store in context.stores if store.name == identifier_name),
            None,
        )
        if store is not None:
            return StoreIdentifierExpression(
                store_name=store.name,
                data_type=store.data_type,
            )
        parameter: Final = next(
            (parameter for parameter in context.parameters if parameter.name == identifier_name),
            None,
        )
        if parameter is not None:
            return ParameterIdentifierExpression(parameter_name=parameter.name)
        variable_definition: Final = next(
            (definition for definition in context.variable_definitions if definition.variable_name == identifier_name),
            None,
        )
        if variable_definition is not None:
            return VariableIdentifierExpression(
                variable_name=variable_definition.variable_name,
                data_type=variable_definition.data_type,
            )
        raise UnknownVariableError(identifier_name)

    def _number_literal(
        self,
        _context: _ParseContext,
    ) -> Expression:
        number_token: Final = self._expect(TokenType.NUMBER_LITERAL, "number literal")  # This is a double-check.
        return NumberLiteralExpression(value=float(number_token.source_location.lexeme))

    def _string_literal(
        self,
        _context: _ParseContext,
    ) -> Expression:
        string_token: Final = self._expect(TokenType.STRING_LITERAL, "string literal")  # This is a double-check.
        return StringLiteralExpression.from_lexeme(string_token.source_location.lexeme)

    def _bool_literal(
        self,
        _context: _ParseContext,
    ) -> Expression:
        bool_token: Final = self._expect(TokenType.BOOL_LITERAL, "boolean literal")  # This is a double-check.
        lexeme: Final = bool_token.source_location.lexeme
        match lexeme:
            case "true":
                value = True
            case "false":
                value = False
            case _:
                msg: Final = f"unexpected boolean literal: {lexeme}"
                raise AssertionError(msg)
        return BoolLiteralExpression(value=value)

    def _unary_operation(
        self,
        context: _ParseContext,
    ) -> Expression:
        unary_operator: Final = _UNARY_OPERATOR_BY_TOKEN_TYPE.get(self._current().type)
        if unary_operator is None:
            msg: Final = f"unexpected unary operator: {self._current().type}"
            raise AssertionError(msg)
        self._advance()
        operand: Final = self._expression(context, Precedence.UNARY)
        return UnaryOperationExpression(operator=unary_operator, operand=operand)

    def _grouped_expression(
        self,
        context: _ParseContext,
    ) -> Expression:
        self._expect(TokenType.LEFT_PARENTHESIS, "'('")  # This is a double-check.
        expression: Final = self._expression(context, Precedence.UNKNOWN)
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
        context: _ParseContext,
    ) -> Expression:
        binary_operator: Final = _BINARY_OPERATOR_BY_TOKEN_TYPE.get(self._current().type)
        if binary_operator is None:
            msg = f"unexpected binary operator: {self._current().type}"
            raise AssertionError(msg)
        precedence: Final = Parser._PARSER_TABLE[self._current().type].infix_precedence
        self._advance()
        right_operand: Final = self._expression(context, precedence)
        return BinaryOperationExpression(left=left_operand, operator=binary_operator, right=right_operand)

    def _ternary_expression(
        self,
        left_operand: Expression,
        context: _ParseContext,
    ) -> Expression:
        if left_operand.get_data_type() != DataType.BOOL:
            raise TernaryConditionTypeError(left_operand.get_data_type())

        self._expect(TokenType.QUESTION_MARK, "'?' in ternary expression")  # This is a double-check.
        true_expression: Final = self._expression(context, Precedence.TERNARY)
        self._expect(TokenType.COLON, "':' in ternary expression")
        false_expression: Final = self._expression(context, Precedence.TERNARY)

        true_data_type: Final = true_expression.get_data_type()
        false_data_type: Final = false_expression.get_data_type()
        if true_data_type != false_data_type:
            raise TernaryOperatorTypeError(true_data_type, false_data_type)

        return TernaryOperationExpression(
            condition=left_operand,
            true_expression=true_expression,
            false_expression=false_expression,
            data_type=true_data_type,
        )

    def _call_operation(
        self,
        left_operand: Expression,
        _context: _ParseContext,
    ) -> Expression:
        self._expect(TokenType.LEFT_PARENTHESIS, "'(' in function call")  # This is a double-check.
        self._expect(TokenType.RIGHT_PARENTHESIS, "')' in function call")
        operand_type: Final = left_operand.get_data_type()
        if operand_type != DataType.STRING:
            raise TypeNotCallableError(operand_type)
        raise NotImplementedError

    _PARSER_TABLE = {
        TokenType.COLON: _TableEntry.unused(),
        TokenType.COMMA: _TableEntry.unused(),
        TokenType.DOLLAR: _TableEntry(_unary_operation, None, Precedence.UNARY),
        TokenType.EXCLAMATION_MARK: _TableEntry(_unary_operation, None, Precedence.UNARY),
        TokenType.HASH: _TableEntry(_unary_operation, None, Precedence.UNARY),
        TokenType.QUESTION_MARK: _TableEntry(None, _ternary_expression, Precedence.TERNARY),
        TokenType.SEMICOLON: _TableEntry.unused(),
        TokenType.EQUALS: _TableEntry.unused(),
        TokenType.EQUALS_EQUALS: _TableEntry(None, _binary_expression, Precedence.EQUALITY),
        TokenType.EXCLAMATION_MARK_EQUALS: _TableEntry(None, _binary_expression, Precedence.EQUALITY),
        TokenType.LESS_THAN: _TableEntry(None, _binary_expression, Precedence.COMPARISON),
        TokenType.LESS_THAN_EQUALS: _TableEntry(None, _binary_expression, Precedence.COMPARISON),
        TokenType.GREATER_THAN: _TableEntry(None, _binary_expression, Precedence.COMPARISON),
        TokenType.GREATER_THAN_EQUALS: _TableEntry(None, _binary_expression, Precedence.COMPARISON),
        TokenType.PLUS: _TableEntry(_unary_operation, _binary_expression, Precedence.SUM),
        TokenType.MINUS: _TableEntry(_unary_operation, _binary_expression, Precedence.SUM),
        TokenType.ASTERISK: _TableEntry(None, _binary_expression, Precedence.PRODUCT),
        TokenType.SLASH: _TableEntry(None, _binary_expression, Precedence.PRODUCT),
        TokenType.LEFT_PARENTHESIS: _TableEntry(_grouped_expression, _call_operation, Precedence.CALL),
        TokenType.RIGHT_PARENTHESIS: _TableEntry.unused(),
        TokenType.STORE: _TableEntry.unused(),
        TokenType.PARAMS: _TableEntry.unused(),
        TokenType.PRINT: _TableEntry.unused(),
        TokenType.LET: _TableEntry.unused(),
        TokenType.IDENTIFIER: _TableEntry(_identifier, None, Precedence.UNARY),
        TokenType.STRING_LITERAL: _TableEntry(_string_literal, None, Precedence.UNARY),
        TokenType.NUMBER_LITERAL: _TableEntry(_number_literal, None, Precedence.UNARY),
        TokenType.BOOL_LITERAL: _TableEntry(_bool_literal, None, Precedence.UNARY),
        TokenType.AND: _TableEntry(None, _binary_expression, Precedence.AND),
        TokenType.OR: _TableEntry(None, _binary_expression, Precedence.OR),
        TokenType.NOT: _TableEntry(_unary_operation, None, Precedence.UNARY),
        TokenType.END_OF_INPUT: _TableEntry.unused(),
    }

    if set(_PARSER_TABLE) != set(TokenType):
        missing_tokens: Final = set(TokenType) - set(_PARSER_TABLE)
        msg: Final = f"Parser table is missing entries for token types: {missing_tokens}"
        raise AssertionError(msg)
