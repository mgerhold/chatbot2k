from collections.abc import Callable
from functools import lru_cache
from typing import Annotated
from typing import Final
from typing import NamedTuple
from typing import Optional
from typing import Self
from typing import cast
from typing import final

from chatbot2k.scripting_engine.precedence import Precedence
from chatbot2k.scripting_engine.token import Token
from chatbot2k.scripting_engine.token_types import TokenType
from chatbot2k.scripting_engine.types.ast import Parameter
from chatbot2k.scripting_engine.types.ast import Script
from chatbot2k.scripting_engine.types.ast import Store
from chatbot2k.scripting_engine.types.data_types import BoolType
from chatbot2k.scripting_engine.types.data_types import DataType
from chatbot2k.scripting_engine.types.data_types import ListType
from chatbot2k.scripting_engine.types.data_types import NumberType
from chatbot2k.scripting_engine.types.data_types import StringType
from chatbot2k.scripting_engine.types.expressions import BinaryOperationExpression
from chatbot2k.scripting_engine.types.expressions import BinaryOperator
from chatbot2k.scripting_engine.types.expressions import BoolLiteralExpression
from chatbot2k.scripting_engine.types.expressions import CallOperationExpression
from chatbot2k.scripting_engine.types.expressions import CollectExpression
from chatbot2k.scripting_engine.types.expressions import Expression
from chatbot2k.scripting_engine.types.expressions import ListComprehensionExpression
from chatbot2k.scripting_engine.types.expressions import ListLiteralExpression
from chatbot2k.scripting_engine.types.expressions import ListOfEmptyListsLiteralExpression
from chatbot2k.scripting_engine.types.expressions import NumberLiteralExpression
from chatbot2k.scripting_engine.types.expressions import ParameterIdentifierExpression
from chatbot2k.scripting_engine.types.expressions import StoreIdentifierExpression
from chatbot2k.scripting_engine.types.expressions import StringLiteralExpression
from chatbot2k.scripting_engine.types.expressions import SubscriptOperationExpression
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
        super().__init__(
            f"Expected {message} at line {start_position.line}, column {start_position.column}, got '{token.type}'."
        )


@final
class StoreRedefinitionError(ParserError):
    def __init__(self, store_name: str) -> None:
        super().__init__(f"Store '{store_name}' is already defined.")


@final
class VariableRedefinitionError(ParserError):
    def __init__(self, variable_name: str) -> None:
        super().__init__(f"Variable '{variable_name}' is already defined.")


@final
class InitializationTypeError(ParserError):
    def __init__(self, variable_name: str, expected_type: DataType, actual_type: Optional[DataType]) -> None:
        if actual_type is None:
            msg = f"Variable '{variable_name}' expected to be initialized with value of type '{expected_type}'."
        else:
            msg = (
                f"Cannot initialize variable '{variable_name}' of type "
                + f"'{expected_type}' with value of type '{actual_type}'."
            )
        super().__init__(msg)


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
class SubscriptOperatorTypeError(ParserError):
    def __init__(self, operand_type: DataType, index_type: DataType) -> None:
        super().__init__(f"Cannot subscript value of type '{operand_type}' with index of type '{index_type}'.")


@final
class AssignmentTypeError(ParserError):
    def __init__(self, lvalue_type: DataType, rvalue_type: DataType) -> None:
        super().__init__(f"Cannot assign value of type '{rvalue_type}' to target of type '{lvalue_type}'.")


@final
class TypeNotCallableError(ParserError):
    def __init__(self, type_: DataType) -> None:
        super().__init__(f"Value of type '{type_}' is not callable.")


@final
class EmptyListLiteralWithoutTypeAnnotationError(ParserError):
    def __init__(self) -> None:
        super().__init__("Empty list literal requires an explicit type annotation.")


@final
class ListElementTypeMismatchError(ParserError):
    def __init__(self, expected_type: DataType, actual_type: DataType) -> None:
        super().__init__(f"List element type mismatch: expected '{expected_type}', got '{actual_type}'.")


@final
class ExpectedEmptyListLiteralError(ParserError):
    def __init__(self, num_elements: int) -> None:
        super().__init__(f"Expected an empty list literal, got a list literal with {num_elements} element(s).")


@final
class ExpectedNonEmptyListLiteralError(ParserError):
    def __init__(self) -> None:
        super().__init__("Expected a non-empty list literal.")


@final
class TypeNotIterableError(ParserError):
    def __init__(self, type_: DataType) -> None:
        super().__init__(f"Value of type '{type_}' is not iterable.")


@final
class NestedListComprehensionsWithoutParenthesesError(ParserError):
    def __init__(self) -> None:
        super().__init__("Nested list comprehensions must be enclosed in parentheses.")


@final
class ListComprehensionConditionTypeError(ParserError):
    def __init__(self, condition_type: DataType) -> None:
        super().__init__(f"List comprehension condition must be of type 'bool', got '{condition_type}'.")


@final
class CollectExpressionTypeError(ParserError):
    def __init__(self, expected_type: DataType, actual_type: DataType) -> None:
        super().__init__(f"Collect expression type error: expected '{expected_type}', got '{actual_type}'.")


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
    TokenType.QUESTION_MARK: UnaryOperator.TO_BOOL,
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
        match expression_type:
            case StringType() | NumberType() | BoolType() | ListType():
                return PrintStatement(argument=expression)
            case _:
                raise ParserTypeError(expression_type)

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

        annotated_type: Optional[DataType] = None
        if self._match(TokenType.COLON):
            # Explicit type annotation given.
            annotated_type = self._data_type()
        self._expect(TokenType.EQUALS, "'=' in variable definition")
        initial_value: Final = self._expression(
            context,
            Precedence.UNKNOWN,
        )

        # Empty list literals are a special case: They require an explicit type annotation.
        if isinstance(initial_value, ListOfEmptyListsLiteralExpression):
            if annotated_type is None:
                raise EmptyListLiteralWithoutTypeAnnotationError()
            if not isinstance(annotated_type, ListType):
                raise InitializationTypeError(identifier_name, annotated_type, None)

            definition = VariableDefinitionStatement(
                variable_name=identifier_name,
                data_type=annotated_type,
                initial_value=_reify_list_of_empty_lists(initial_value, annotated_type),
            )
            context.variable_definitions.append(definition)
            return definition

        initial_value_type: Final = initial_value.get_data_type()
        if annotated_type is not None and annotated_type != initial_value_type:
            raise InitializationTypeError(identifier_name, annotated_type, initial_value_type)
        definition = VariableDefinitionStatement(
            variable_name=identifier_name,
            data_type=initial_value_type,
            initial_value=initial_value,
        )
        context.variable_definitions.append(definition)
        return definition

    def _data_type(self) -> DataType:
        match self._current().type:
            case TokenType.STRING:
                self._advance()
                return StringType()
            case TokenType.NUMBER:
                self._advance()
                return NumberType()
            case TokenType.BOOL:
                self._advance()
                return BoolType()
            case TokenType.LIST:
                self._advance()
                self._expect(TokenType.LESS_THAN, "'<' in list type")
                element_type: Final = self._data_type()
                self._expect(TokenType.GREATER_THAN, "'>' in list type")
                return ListType(of_type=element_type)
            case _:
                raise ExpectedTokenError(self._current(), "data type")

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
        if not isinstance(left_operand.get_data_type(), BoolType):
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
        context: _ParseContext,
    ) -> Expression:
        self._expect(TokenType.LEFT_PARENTHESIS, "'(' in function call")  # This is a double-check.
        arguments: Final[list[Expression]] = []
        while True:
            if self._match(TokenType.RIGHT_PARENTHESIS) is not None:
                break
            arguments.append(self._expression(context, Precedence.UNKNOWN))
            if self._match(TokenType.COMMA) is None:
                self._expect(TokenType.RIGHT_PARENTHESIS, "')' after function call arguments")
                break
        operand_type: Final = left_operand.get_data_type()
        if not isinstance(operand_type, StringType):
            raise TypeNotCallableError(operand_type)
        return CallOperationExpression(
            callee=left_operand,
            arguments=arguments,
        )

    def _list_literal(
        self,
        context: _ParseContext,
    ) -> Expression:
        self._expect(TokenType.LEFT_SQUARE_BRACKET, "'[' in list literal")  # This is a double-check.
        elements: Final[list[Expression]] = []
        while True:
            if self._match(TokenType.RIGHT_SQUARE_BRACKET) is not None:
                break
            elements.append(self._expression(context, Precedence.UNKNOWN))
            if self._match(TokenType.COMMA) is None:
                self._expect(TokenType.RIGHT_SQUARE_BRACKET, "']' after list literal elements")
                break

        if not elements:
            return ListOfEmptyListsLiteralExpression(nested_empty_lists=[])

        # If a list contains empty list literals, they are not considered during type checking.
        # However, at least one non-empty element must be present to infer the list's element type.
        temp_elements: Final[list[Expression]] = []  # May contain `ListOfEmptyListsLiteralExpression` objects.
        inferred_element_type: Optional[DataType] = None
        for element in elements:
            match element:
                case ListOfEmptyListsLiteralExpression():
                    temp_elements.append(element)
                case _:
                    element_type = element.get_data_type()
                    if inferred_element_type is None:
                        inferred_element_type = element_type
                    elif inferred_element_type != element_type:
                        raise ListElementTypeMismatchError(inferred_element_type, element_type)
                    temp_elements.append(element)

        if all(isinstance(element, ListOfEmptyListsLiteralExpression) for element in temp_elements):
            return ListOfEmptyListsLiteralExpression(
                nested_empty_lists=cast(list[ListOfEmptyListsLiteralExpression], elements)
            )
        assert inferred_element_type is not None, "The check above this line catches this."

        if any(isinstance(element, ListOfEmptyListsLiteralExpression) for element in temp_elements) and not isinstance(
            inferred_element_type, ListType
        ):
            # There are list literals inside this list, but there's also a non-list element.
            raise ListElementTypeMismatchError(
                expected_type=ListType(of_type=inferred_element_type),
                actual_type=inferred_element_type,
            )
        inferred_elements: Final[list[Expression]] = []
        for temp_element in temp_elements:
            match temp_element:
                case ListOfEmptyListsLiteralExpression():
                    assert isinstance(inferred_element_type, ListType), "We checked this above."
                    # Promote to empty list of known type.
                    inferred_elements.append(_reify_list_of_empty_lists(temp_element, data_type=inferred_element_type))
                case _:
                    inferred_elements.append(temp_element)
        return ListLiteralExpression(
            elements=inferred_elements,
            element_type=inferred_element_type,
        )

    def _subscript_operator(
        self,
        left_operand: Expression,
        context: _ParseContext,
    ) -> Expression:
        self._expect(TokenType.LEFT_SQUARE_BRACKET, "'[' in subscript operation")  # This is a double-check.
        index_expression: Final = self._expression(context, Precedence.UNKNOWN)
        self._expect(TokenType.RIGHT_SQUARE_BRACKET, "']' after subscript index")
        operand_type: Final = left_operand.get_data_type()
        index_type: Final = index_expression.get_data_type()
        match operand_type, index_type:
            case StringType(), NumberType():
                return SubscriptOperationExpression(
                    operand=left_operand,
                    index=index_expression,
                    data_type=StringType(),
                )
            case ListType(of_type=element_type), NumberType():
                return SubscriptOperationExpression(
                    operand=left_operand,
                    index=index_expression,
                    data_type=element_type,
                )
            case _, _:
                raise SubscriptOperatorTypeError(operand_type, index_type)

    def _list_comprehension(
        self,
        context: _ParseContext,
    ) -> Expression:
        self._expect(TokenType.FOR, "'for' in list comprehension")  # This is a double-check.
        iterable: Final = self._expression(context, Precedence.UNKNOWN)
        iterable_type: Final = iterable.get_data_type()
        loop_variable_type: DataType
        match iterable_type:
            case StringType():
                loop_variable_type = StringType()
            case ListType(of_type=element_type):
                loop_variable_type = element_type
            case _:
                raise TypeNotIterableError(iterable_type)

        self._expect(TokenType.AS, "'as' in list comprehension")
        loop_variable_identifier: Final = self._expect(TokenType.IDENTIFIER, "loop variable name")
        loop_variable_name: Final = loop_variable_identifier.source_location.lexeme
        self._ensure_not_shadowed(loop_variable_name, context)
        context.variable_definitions.append(
            VariableDefinitionStatement(
                variable_name=loop_variable_name,
                data_type=loop_variable_type,
                initial_value=_create_default_value_expression(loop_variable_type),
            )
        )
        condition: Final = (
            self._expression(context, Precedence.UNKNOWN) if self._match(TokenType.IF) is not None else None
        )
        if condition is not None and not isinstance(condition.get_data_type(), BoolType):
            raise ListComprehensionConditionTypeError(condition.get_data_type())
        self._expect(TokenType.YEET, "'yeet' in list comprehension")
        if self._current().type == TokenType.FOR:
            # For better readability, we forbid nested list comprehensions without explicit parentheses.
            raise NestedListComprehensionsWithoutParenthesesError()

        yield_expression: Final = self._expression(context, Precedence.UNKNOWN)
        # We remove the loop variable from the context after parsing the comprehension. This way, we simulate
        # having scopes, although we don't really support scopes.
        context.variable_definitions.pop()
        return ListComprehensionExpression(
            iterable=iterable,
            element_variable_name=loop_variable_name,
            condition=condition,
            expression=yield_expression,
        )

    def _collect(
        self,
        context: _ParseContext,
    ) -> Expression:
        self._expect(TokenType.COLLECT, "'collect' in collect expression")  # This is a double-check.
        iterable: Final = self._expression(context, Precedence.UNKNOWN)
        iterable_type: Final = iterable.get_data_type()
        element_type: DataType
        match iterable_type:
            case StringType():
                element_type = StringType()
            case ListType(of_type=element_type_):
                element_type = element_type_
            case _:
                raise TypeNotIterableError(iterable_type)
        self._expect(TokenType.AS, "'as' in collect expression")
        accumulator_identifier: Final = self._expect(TokenType.IDENTIFIER, "accumulator identifier")
        accumulator_name: Final = accumulator_identifier.source_location.lexeme
        self._ensure_not_shadowed(accumulator_name, context)
        self._expect(TokenType.COMMA, "',' in collect expression")
        element_identifier: Final = self._expect(TokenType.IDENTIFIER, "element identifier")
        element_name: Final = element_identifier.source_location.lexeme
        self._ensure_not_shadowed(element_name, context)
        context.variable_definitions.append(
            VariableDefinitionStatement(
                variable_name=accumulator_name,
                data_type=element_type,
                initial_value=_create_default_value_expression(ListType(of_type=element_type)),
            )
        )
        context.variable_definitions.append(
            VariableDefinitionStatement(
                variable_name=element_name,
                data_type=element_type,
                initial_value=_create_default_value_expression(element_type),
            )
        )
        self._expect(TokenType.WITH, "'with' in collect expression")
        collection_expression: Final = self._expression(context, Precedence.UNKNOWN)
        collection_expression_type: Final = collection_expression.get_data_type()
        if collection_expression_type != element_type:
            raise CollectExpressionTypeError(
                expected_type=element_type,
                actual_type=collection_expression_type,
            )
        # We remove the accumulator and element variables from the context after parsing the collect expression.
        # This way, we simulate having scopes, although we don't really support scopes.
        context.variable_definitions.pop()
        context.variable_definitions.pop()
        return CollectExpression(
            iterable=iterable,
            accumulator_variable_name=accumulator_name,
            element_variable_name=element_name,
            expression=collection_expression,
        )

    def _ensure_not_shadowed(
        self,
        identifier_name: str,
        context: _ParseContext,
    ) -> None:
        if next((store.name for store in context.stores if store.name == identifier_name), None) is not None:
            raise VariableShadowsStoreError(identifier_name)
        if (
            next((parameter.name for parameter in context.parameters if parameter.name == identifier_name), None)
            is not None
        ):
            raise VariableShadowsParameterError(identifier_name)
        if (
            next(
                (
                    definition
                    for definition in context.variable_definitions
                    if definition.variable_name == identifier_name
                ),
                None,
            )
            is not None
        ):
            raise VariableRedefinitionError(identifier_name)

    _PARSER_TABLE = {
        TokenType.COLON: _TableEntry.unused(),
        TokenType.COMMA: _TableEntry.unused(),
        TokenType.DOLLAR: _TableEntry(_unary_operation, None, Precedence.UNARY),
        TokenType.EXCLAMATION_MARK: _TableEntry(_unary_operation, None, Precedence.UNARY),
        TokenType.HASH: _TableEntry(_unary_operation, None, Precedence.UNARY),
        TokenType.QUESTION_MARK: _TableEntry(_unary_operation, _ternary_expression, Precedence.TERNARY),
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
        TokenType.LEFT_SQUARE_BRACKET: _TableEntry(_list_literal, _subscript_operator, Precedence.CALL),
        TokenType.RIGHT_SQUARE_BRACKET: _TableEntry.unused(),
        TokenType.STORE: _TableEntry.unused(),
        TokenType.PARAMS: _TableEntry.unused(),
        TokenType.PRINT: _TableEntry.unused(),
        TokenType.LET: _TableEntry.unused(),
        TokenType.IDENTIFIER: _TableEntry(_identifier, None, Precedence.UNARY),
        TokenType.STRING_LITERAL: _TableEntry(_string_literal, None, Precedence.UNARY),
        TokenType.NUMBER_LITERAL: _TableEntry(_number_literal, None, Precedence.UNARY),
        TokenType.BOOL_LITERAL: _TableEntry(_bool_literal, None, Precedence.UNARY),
        TokenType.STRING: _TableEntry.unused(),
        TokenType.NUMBER: _TableEntry.unused(),
        TokenType.BOOL: _TableEntry.unused(),
        TokenType.LIST: _TableEntry.unused(),
        TokenType.AND: _TableEntry(None, _binary_expression, Precedence.AND),
        TokenType.OR: _TableEntry(None, _binary_expression, Precedence.OR),
        TokenType.NOT: _TableEntry(_unary_operation, None, Precedence.UNARY),
        TokenType.FOR: _TableEntry(_list_comprehension, None, Precedence.UNKNOWN),
        TokenType.AS: _TableEntry.unused(),
        TokenType.IF: _TableEntry.unused(),
        TokenType.YEET: _TableEntry.unused(),
        TokenType.COLLECT: _TableEntry(_collect, None, Precedence.UNKNOWN),
        TokenType.WITH: _TableEntry.unused(),
        TokenType.END_OF_INPUT: _TableEntry.unused(),
    }

    if set(_PARSER_TABLE) != set(TokenType):
        missing_tokens: Final = set(TokenType) - set(_PARSER_TABLE)
        msg: Final = f"Parser table is missing entries for token types: {missing_tokens}"
        raise AssertionError(msg)


def _reify_list_of_empty_lists(
    literal: ListOfEmptyListsLiteralExpression,
    data_type: ListType,
) -> ListLiteralExpression:
    if isinstance(data_type.of_type, ListType):
        sub_lists: Final[list[Expression]] = [
            _reify_list_of_empty_lists(literal=sub_literal, data_type=data_type.of_type)
            for sub_literal in literal.nested_empty_lists
        ]
        return ListLiteralExpression(elements=sub_lists, element_type=data_type.of_type)
    elif literal.nested_empty_lists:
        raise ExpectedEmptyListLiteralError(len(literal.nested_empty_lists))
    else:
        return ListLiteralExpression(elements=[], element_type=data_type.of_type)


def _create_default_value_expression(data_type: DataType) -> Expression:
    match data_type:
        case StringType():
            return StringLiteralExpression(value="")
        case NumberType():
            return NumberLiteralExpression(value=0.0)
        case BoolType():
            return BoolLiteralExpression(value=False)
        case ListType(of_type=element_type):
            return ListLiteralExpression(elements=[], element_type=element_type)
