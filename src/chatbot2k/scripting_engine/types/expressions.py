from abc import ABC
from abc import abstractmethod
from enum import StrEnum
from typing import Annotated
from typing import Final
from typing import Literal
from typing import Optional
from typing import Self
from typing import cast
from typing import final
from typing import override

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Discriminator

from chatbot2k.scripting_engine.escape_characters import ESCAPE_CHARACTERS
from chatbot2k.scripting_engine.lexer import LexerError
from chatbot2k.scripting_engine.stores import AlwaysEmptyPersistentStore
from chatbot2k.scripting_engine.stores import StoreKey
from chatbot2k.scripting_engine.token_types import TokenType
from chatbot2k.scripting_engine.types.builtins import BUILTIN_FUNCTIONS
from chatbot2k.scripting_engine.types.data_types import BoolType
from chatbot2k.scripting_engine.types.data_types import DataType
from chatbot2k.scripting_engine.types.data_types import ListType
from chatbot2k.scripting_engine.types.data_types import NumberType
from chatbot2k.scripting_engine.types.data_types import StringType
from chatbot2k.scripting_engine.types.execution_context import ExecutionContext
from chatbot2k.scripting_engine.types.execution_error import ExecutionError
from chatbot2k.scripting_engine.types.value import BoolValue
from chatbot2k.scripting_engine.types.value import ListValue
from chatbot2k.scripting_engine.types.value import NumberValue
from chatbot2k.scripting_engine.types.value import StringValue
from chatbot2k.scripting_engine.types.value import Value


@final
class ExpressionType(StrEnum):
    STRING_LITERAL = "string_literal"
    NUMBER_LITERAL = "number_literal"
    BOOL_LITERAL = "bool_literal"
    STORE_IDENTIFIER = "store_identifier"
    PARAMETER_IDENTIFIER = "parameter_identifier"
    VARIABLE_IDENTIFIER = "variable_identifier"
    UNARY_OPERATION = "unary_operation"
    BINARY_OPERATION = "binary_operation"
    TERNARY_OPERATION = "ternary_operation"
    CALL_OPERATION = "call_operation"
    EMPTY_LIST_LITERAL = "empty_list_literal"
    LIST_OF_EMPTY_LISTS_LITERAL = "list_of_empty_lists_literal"
    LIST_LITERAL = "list_literal"
    SUBSCRIPT_OPERATION = "subscript_operation"
    LIST_COMPREHENSION = "list_comprehension"
    FOLD = "fold"
    SPLIT_OPERATION = "split_operation"
    JOIN_OPERATION = "join_operation"
    SORT_OPERATION = "sort_operation"


class BaseExpression(BaseModel, ABC):
    @abstractmethod
    def get_data_type(self) -> DataType: ...

    @abstractmethod
    async def evaluate(
        self,
        context: ExecutionContext,
    ) -> Value: ...


@final
class StringLiteralExpression(BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.STRING_LITERAL] = ExpressionType.STRING_LITERAL
    value: str

    @override
    def get_data_type(self) -> DataType:
        return StringType()

    @override
    async def evaluate(self, context: ExecutionContext) -> Value:
        return StringValue(value=self.value)

    @classmethod
    def from_lexeme(cls, lexeme: str) -> Self:
        if not lexeme.startswith("'") or not lexeme.endswith("'"):
            msg = f"Invalid string lexeme: {lexeme}"
            raise AssertionError(msg)
        escaped_string = ""

        i = 1
        while i < len(lexeme) - 1:
            current = lexeme[i]
            if current == "\\" and i + 1 < len(lexeme) - 1:
                next_ = lexeme[i + 1]
                escaped_char = ESCAPE_CHARACTERS.get(next_)
                if escaped_char is None:
                    msg = f"Invalid escape sequence: \\{next_}"
                    raise AssertionError(msg)
                escaped_string += escaped_char
                i += 2
            else:
                escaped_string += current
                i += 1

        return cls(value=escaped_string)


@final
class NumberLiteralExpression(BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.NUMBER_LITERAL] = ExpressionType.NUMBER_LITERAL
    value: float

    @override
    def get_data_type(self) -> DataType:
        return NumberType()

    @override
    async def evaluate(
        self,
        context: ExecutionContext,
    ) -> Value:
        return NumberValue(value=self.value)


@final
class BoolLiteralExpression(BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.BOOL_LITERAL] = ExpressionType.BOOL_LITERAL
    value: bool

    @override
    def get_data_type(self) -> DataType:
        return BoolType()

    @override
    async def evaluate(
        self,
        context: ExecutionContext,
    ) -> Value:
        return BoolValue(value=self.value)


@final
class StoreIdentifierExpression(BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.STORE_IDENTIFIER] = ExpressionType.STORE_IDENTIFIER
    store_name: str
    data_type: DataType

    @override
    def get_data_type(self) -> DataType:
        return self.data_type

    @override
    async def evaluate(
        self,
        context: ExecutionContext,
    ) -> Value:
        store_key: Final = StoreKey(
            script_name=context.call_stack[-1],
            store_name=self.store_name,
        )
        value: Final = context.stores.get(store_key)
        if value is None:
            msg = f"Store '{self.store_name}' not found."
            raise ExecutionError(msg)
        if value.get_data_type() != self.data_type:
            msg = (
                f"Type mismatch when accessing store '{self.store_name}': "
                + f"expected {self.data_type}, got {value.get_data_type()}"
            )
            raise ExecutionError(msg)
        return value


@final
class ParameterIdentifierExpression(BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.PARAMETER_IDENTIFIER] = ExpressionType.PARAMETER_IDENTIFIER
    parameter_name: str

    @override
    def get_data_type(self) -> DataType:
        # All parameters are strings.
        return StringType()

    @override
    async def evaluate(
        self,
        context: ExecutionContext,
    ) -> Value:
        value: Final = context.parameters.get(self.parameter_name)
        if value is None:
            msg = f"Parameter '{self.parameter_name}' not defined."
            raise ExecutionError(msg)
        if value.get_data_type() != StringType():
            msg = (
                f"Type mismatch when accessing parameter '{self.parameter_name}': "
                + f"expected {StringType()}, got {value.get_data_type()}"
            )
            raise ExecutionError(msg)
        return value


@final
class VariableIdentifierExpression(BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.VARIABLE_IDENTIFIER] = ExpressionType.VARIABLE_IDENTIFIER
    variable_name: str
    data_type: DataType

    @override
    def get_data_type(self) -> DataType:
        return self.data_type

    @override
    async def evaluate(
        self,
        context: ExecutionContext,
    ) -> Value:
        value: Final = context.variables.get(self.variable_name)
        if value is None:
            msg = f"Variable '{self.variable_name}' not defined."
            raise ExecutionError(msg)
        if value.get_data_type() != self.data_type:
            msg = (
                f"Type mismatch when accessing variable '{self.variable_name}': "
                + f"expected {self.data_type}, got {value.get_data_type()}"
            )
            raise ExecutionError(msg)
        return value


@final
class BinaryOperator(StrEnum):
    ADD = "+"
    SUBTRACT = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    MODULO = "%"

    EQUALS = "=="
    NOT_EQUALS = "!="
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="

    AND = "and"
    OR = "or"

    RANGE_INCLUSIVE = "..="
    RANGE_EXCLUSIVE = "..<"


@final
class UnaryOperator(StrEnum):
    PLUS = "+"
    NEGATE = "-"
    TO_NUMBER = "$"
    TO_STRING = "#"
    TO_BOOL = "?"
    EVALUATE = "!"
    NOT = "not"


@final
class UnaryOperationExpression(BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.UNARY_OPERATION] = ExpressionType.UNARY_OPERATION
    operator: UnaryOperator
    operand: "Expression"

    @override
    def get_data_type(self) -> DataType:
        operand_type: Final = self.operand.get_data_type()
        match self.operator, operand_type:
            case (UnaryOperator.PLUS | UnaryOperator.NEGATE, NumberType()):
                return NumberType()
            case (UnaryOperator.NOT, BoolType()):
                return BoolType()
            case (UnaryOperator.TO_NUMBER, BoolType() | NumberType() | StringType()):
                return NumberType()
            case (UnaryOperator.TO_STRING, BoolType() | NumberType() | StringType()):
                return StringType()
            case (UnaryOperator.TO_BOOL, BoolType() | NumberType() | StringType()):
                return BoolType()
            case (UnaryOperator.EVALUATE, StringType()):
                return StringType()
            case (
                UnaryOperator.PLUS
                | UnaryOperator.NEGATE
                | UnaryOperator.TO_NUMBER
                | UnaryOperator.TO_BOOL
                | UnaryOperator.TO_STRING
                | UnaryOperator.EVALUATE
                | UnaryOperator.NOT,
                _,
            ):
                msg: Final = f"Unary operator {self.operator} is not supported for {operand_type} operands"
                raise TypeError(msg)

    @override
    async def evaluate(
        self,
        context: ExecutionContext,
    ) -> Value:
        from chatbot2k.scripting_engine.lexer import Lexer
        from chatbot2k.scripting_engine.parser import Parser

        operand_value: Final = await self.operand.evaluate(context)
        match self.operator, operand_value:
            case UnaryOperator.PLUS | UnaryOperator.TO_NUMBER, NumberValue(value=v):
                return NumberValue(value=v)
            case UnaryOperator.NEGATE, NumberValue(value=v):
                return NumberValue(value=-v)
            case UnaryOperator.NOT, BoolValue(value=v):
                return BoolValue(value=not v)
            case UnaryOperator.TO_NUMBER, BoolValue(value=value):
                return NumberValue(value=1 if value else 0)
            case UnaryOperator.TO_NUMBER, StringValue(value=value):
                try:
                    lexer = Lexer(value)
                    tokens: Final = lexer.tokenize()
                except LexerError as e:
                    msg = f"Failed to lex string '{value}' for number conversion: {str(e)}"
                    raise ExecutionError(msg) from e
                msg = f"String '{value}' does not represent a valid number"
                if len(tokens) < 2:
                    raise ExecutionError(msg)
                match tokens[0].type, tokens[1].type:
                    case TokenType.NUMBER_LITERAL, TokenType.END_OF_INPUT:
                        return NumberValue(value=float(tokens[0].source_location.lexeme))
                    case TokenType.PLUS, TokenType.NUMBER_LITERAL:
                        return NumberValue(value=float(tokens[1].source_location.lexeme))
                    case TokenType.MINUS, TokenType.NUMBER_LITERAL:
                        return NumberValue(value=-float(tokens[1].source_location.lexeme))
                    case _:
                        raise ExecutionError(msg)
            case UnaryOperator.EVALUATE, StringValue(value=source_code):
                try:
                    lexer = Lexer(source_code)
                    parser: Final = Parser("", lexer.tokenize())
                    script: Final = parser.parse()
                except Exception as e:
                    msg = f"Failed to parse code for evaluation: {str(e)}"
                    raise ExecutionError(msg) from e
                if script.stores:
                    raise ExecutionError("Stores inside evaluated code are not supported")
                if script.parameters:
                    raise ExecutionError("Parameters inside evaluated code are not supported")
                script_output: Final = await script.execute(
                    AlwaysEmptyPersistentStore(),
                    [],
                    call_script=context.call_script,
                )
                if script_output is None:
                    raise ExecutionError("Evaluated script did not produce any output")
                return StringValue(value=script_output)
            case (UnaryOperator.TO_STRING, BoolValue(value=v)):
                return StringValue(value="true" if v else "false")
            case (UnaryOperator.TO_STRING, NumberValue(value=v)):
                return StringValue(value=str(int(v)) if v.is_integer() else str(v))
            case (UnaryOperator.TO_STRING, StringValue(value=v)):
                return StringValue(value=v)
            case (UnaryOperator.TO_BOOL, BoolValue(value=v)):
                return BoolValue(value=v)
            case (UnaryOperator.TO_BOOL, NumberValue(value=v)):
                return BoolValue(value=v != 0.0)
            case (UnaryOperator.TO_BOOL, StringValue(value=v)):
                match v:
                    case "true":
                        return BoolValue(value=True)
                    case "false":
                        return BoolValue(value=False)
                    case _:
                        msg = f"String '{v}' cannot be converted to boolean"
                        raise ExecutionError(msg)
            case (
                UnaryOperator.PLUS
                | UnaryOperator.NEGATE
                | UnaryOperator.TO_NUMBER
                | UnaryOperator.TO_BOOL
                | UnaryOperator.TO_STRING
                | UnaryOperator.EVALUATE
                | UnaryOperator.NOT,
                _,
            ):
                msg = f"Unary operator {self.operator} is not supported for {operand_value.get_data_type()} operands"
                raise ExecutionError(msg)


@final
class BinaryOperationExpression(BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.BINARY_OPERATION] = ExpressionType.BINARY_OPERATION
    left: "Expression"
    operator: BinaryOperator
    right: "Expression"

    @override
    def get_data_type(self) -> DataType:
        match self.left.get_data_type(), self.operator, self.right.get_data_type():
            case (
                (BoolType(), BinaryOperator.EQUALS, BoolType())
                | (BoolType(), BinaryOperator.NOT_EQUALS, BoolType())
                | (NumberType(), BinaryOperator.EQUALS, NumberType())
                | (NumberType(), BinaryOperator.NOT_EQUALS, NumberType())
                | (NumberType(), BinaryOperator.LESS_THAN, NumberType())
                | (NumberType(), BinaryOperator.LESS_THAN_OR_EQUAL, NumberType())
                | (NumberType(), BinaryOperator.GREATER_THAN, NumberType())
                | (NumberType(), BinaryOperator.GREATER_THAN_OR_EQUAL, NumberType())
                | (StringType(), BinaryOperator.EQUALS, StringType())
                | (StringType(), BinaryOperator.NOT_EQUALS, StringType())
                | (StringType(), BinaryOperator.LESS_THAN, StringType())
                | (StringType(), BinaryOperator.LESS_THAN_OR_EQUAL, StringType())
                | (StringType(), BinaryOperator.GREATER_THAN, StringType())
                | (StringType(), BinaryOperator.GREATER_THAN_OR_EQUAL, StringType())
            ):
                return BoolType()
            case (BoolType(), BinaryOperator.AND, BoolType()) | (BoolType(), BinaryOperator.OR, BoolType()):
                return BoolType()
            case (
                (NumberType(), BinaryOperator.ADD, NumberType())
                | (NumberType(), BinaryOperator.SUBTRACT, NumberType())
                | (NumberType(), BinaryOperator.MULTIPLY, NumberType())
                | (NumberType(), BinaryOperator.DIVIDE, NumberType())
                | (NumberType(), BinaryOperator.MODULO, NumberType())
            ):
                return NumberType()
            case (StringType(), BinaryOperator.ADD, StringType()):
                return StringType()
            case (NumberType(), BinaryOperator.RANGE_INCLUSIVE, NumberType()) | (
                NumberType(),
                BinaryOperator.RANGE_EXCLUSIVE,
                NumberType(),
            ):
                return ListType(of_type=NumberType())
            case (_, BinaryOperator.RANGE_INCLUSIVE, _) | (_, BinaryOperator.RANGE_EXCLUSIVE, _):
                operator_name: Final = "..=" if self.operator == BinaryOperator.RANGE_INCLUSIVE else "..<"
                left_data_type: Final = self.left.get_data_type()
                right_data_type: Final = self.right.get_data_type()
                if left_data_type != NumberType():
                    msg = f"Range operator {operator_name} requires number operands, got '{left_data_type}' for start"
                else:
                    msg = f"Range operator {operator_name} requires number operands, got '{right_data_type}' for end"
                raise TypeError(msg)
            case (ListType(of_type=left_type), BinaryOperator.ADD, ListType(of_type=right_type)):
                if left_type != right_type:
                    msg = f"Operator {self.operator} is not supported for list operands of different element types"
                    raise TypeError(msg)
                return ListType(of_type=left_type)
            case (NumberType(), _, _) | (_, _, NumberType()):
                msg = f"Operator {self.operator} is not supported for number operands"
                raise TypeError(msg)
            case (StringType(), _, _) | (_, _, StringType()):
                msg = f"Operator {self.operator} is not supported for string operands"
                raise TypeError(msg)
            # TODO: Create minimal example and file a Pyright issue about this false positive.
            case (BoolType(), _, _) | (_, _, BoolType()):  # type: ignore[reportUnnecessaryComparison]
                msg = f"Operator {self.operator} is not supported for boolean operands"
                raise TypeError(msg)
            case (ListType(), _, _) | (_, _, ListType()):
                msg = f"Operator {self.operator} is not supported for list operands"
                raise TypeError(msg)
            case _:
                # Pyright's exhaustiveness check doesn't seem to work here. We should
                # not really need the default case.
                msg = (
                    f"Operator {self.operator} is not supported for the given operand types "
                    + f"'{self.left.get_data_type()}' and '{self.right.get_data_type()}'"
                )
                raise TypeError(msg)

    @override
    async def evaluate(
        self,
        context: ExecutionContext,
    ) -> Value:
        left_value: Final = await self.left.evaluate(context)
        right_value: Final = await self.right.evaluate(context)
        match left_value, self.operator, right_value:
            case (
                (BoolValue(value=l), BinaryOperator.EQUALS, BoolValue(value=r))
                | (NumberValue(value=l), BinaryOperator.EQUALS, NumberValue(value=r))
                | (StringValue(value=l), BinaryOperator.EQUALS, StringValue(value=r))
            ):
                return BoolValue(value=l == r)
            case (
                (BoolValue(value=l), BinaryOperator.NOT_EQUALS, BoolValue(value=r))
                | (NumberValue(value=l), BinaryOperator.NOT_EQUALS, NumberValue(value=r))
                | (StringValue(value=l), BinaryOperator.NOT_EQUALS, StringValue(value=r))
            ):
                return BoolValue(value=l != r)
            case NumberValue(value=l), BinaryOperator.LESS_THAN, NumberValue(value=r):
                return BoolValue(value=l < r)
            case NumberValue(value=l), BinaryOperator.LESS_THAN_OR_EQUAL, NumberValue(value=r):
                return BoolValue(value=l <= r)
            case NumberValue(value=l), BinaryOperator.GREATER_THAN, NumberValue(value=r):
                return BoolValue(value=l > r)
            case NumberValue(value=l), BinaryOperator.GREATER_THAN_OR_EQUAL, NumberValue(value=r):
                return BoolValue(value=l >= r)
            case StringValue(value=l), BinaryOperator.LESS_THAN, StringValue(value=r):
                return BoolValue(value=l < r)
            case StringValue(value=l), BinaryOperator.LESS_THAN_OR_EQUAL, StringValue(value=r):
                return BoolValue(value=l <= r)
            case StringValue(value=l), BinaryOperator.GREATER_THAN, StringValue(value=r):
                return BoolValue(value=l > r)
            case StringValue(value=l), BinaryOperator.GREATER_THAN_OR_EQUAL, StringValue(value=r):
                return BoolValue(value=l >= r)
            case BoolValue(value=l), BinaryOperator.AND, BoolValue(value=r):
                return BoolValue(value=l and r)
            case BoolValue(value=l), BinaryOperator.OR, BoolValue(value=r):
                return BoolValue(value=l or r)
            case NumberValue(value=l), BinaryOperator.ADD, NumberValue(value=r):
                return NumberValue(value=l + r)
            case NumberValue(value=l), BinaryOperator.SUBTRACT, NumberValue(value=r):
                return NumberValue(value=l - r)
            case NumberValue(value=l), BinaryOperator.MULTIPLY, NumberValue(value=r):
                return NumberValue(value=l * r)
            case NumberValue(value=l), BinaryOperator.DIVIDE, NumberValue(value=r):
                if r == 0:
                    msg = "Division by zero"
                    raise ExecutionError(msg)
                return NumberValue(value=l / r)
            case NumberValue(value=l), BinaryOperator.MODULO, NumberValue(value=r):
                if r == 0:
                    msg = "Modulo by zero"
                    raise ExecutionError(msg)
                return NumberValue(value=l % r)
            case StringValue(value=l), BinaryOperator.ADD, StringValue(value=r):
                return StringValue(value=l + r)
            case NumberValue(value=l), BinaryOperator.RANGE_INCLUSIVE, NumberValue(value=r):
                if not l.is_integer():
                    msg = f"Range operator ..= requires integer operands, got non-integer start value {l}"
                    raise ExecutionError(msg)
                if not r.is_integer():
                    msg = f"Range operator ..= requires integer operands, got non-integer end value {r}"
                    raise ExecutionError(msg)

                start_int = int(l)
                end_int = int(r)

                if start_int <= end_int:
                    elements = [NumberValue(value=float(i)) for i in range(start_int, end_int + 1)]
                else:
                    elements = [NumberValue(value=float(i)) for i in range(start_int, end_int - 1, -1)]

                return ListValue(elements=cast(list[Value], elements), element_type=NumberType())
            case NumberValue(value=l), BinaryOperator.RANGE_EXCLUSIVE, NumberValue(value=r):
                if not l.is_integer():
                    msg = f"Range operator ..< requires integer operands, got non-integer start value {l}"
                    raise ExecutionError(msg)
                if not r.is_integer():
                    msg = f"Range operator ..< requires integer operands, got non-integer end value {r}"
                    raise ExecutionError(msg)

                start_int = int(l)
                end_int = int(r)

                if start_int <= end_int:
                    elements = [NumberValue(value=float(i)) for i in range(start_int, end_int)]
                else:
                    elements = [NumberValue(value=float(i)) for i in range(start_int, end_int, -1)]

                return ListValue(elements=cast(list[Value], elements), element_type=NumberType())
            case (
                ListValue(elements=l, element_type=l_type),
                BinaryOperator.ADD,
                ListValue(elements=r, element_type=r_type),
            ):
                if l_type != r_type:
                    msg = "Cannot concatenate lists of different element types: " + f"'{l_type}' and '{r_type}'"
                    raise ExecutionError(msg)
                return ListValue(elements=l + r, element_type=l_type)
            case _:
                msg = (
                    f"Operator {self.operator} is not supported for the given operand types "
                    + f"'{left_value.get_data_type()}' and '{right_value.get_data_type()}'"
                )
                raise ExecutionError(msg)


@final
class TernaryOperationExpression(BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.TERNARY_OPERATION] = ExpressionType.TERNARY_OPERATION
    condition: "Expression"
    true_expression: "Expression"
    false_expression: "Expression"
    data_type: DataType

    @override
    def get_data_type(self) -> DataType:
        return self.data_type

    @override
    async def evaluate(
        self,
        context: ExecutionContext,
    ) -> Value:
        predicate: Final = await self.condition.evaluate(context)
        if predicate.get_data_type() != BoolType():
            msg = f"Ternary condition must be a boolean, got {predicate.get_data_type()}"
            raise ExecutionError(msg)
        assert isinstance(predicate, BoolValue)
        if predicate.value:
            return await self.true_expression.evaluate(context)
        return await self.false_expression.evaluate(context)


@final
class CallOperationExpression(BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.CALL_OPERATION] = ExpressionType.CALL_OPERATION
    callee: "Expression"
    arguments: "list[Expression]"

    @override
    def get_data_type(self) -> DataType:
        return StringType()

    @override
    async def evaluate(
        self,
        context: ExecutionContext,
    ) -> Value:
        callee_name: Final = await self.callee.evaluate(context)
        if not isinstance(callee_name, StringValue):
            msg: Final = f"Callee must be a string, got {callee_name.get_data_type()}."
            raise ExecutionError(msg)

        builtin_function: Final = BUILTIN_FUNCTIONS.get(callee_name.value)
        if builtin_function is not None:
            return StringValue(value=await builtin_function(*self.arguments, context=context))

        context.call_stack.append(callee_name.value)
        evaluated_arguments: Final = [await argument.evaluate(context) for argument in self.arguments]
        return_value: Final = await context.call_script(
            callee_name.value,
            *(argument.to_string() for argument in evaluated_arguments),
        )
        context.call_stack.pop()
        return StringValue(value=return_value)


@final
class ListOfEmptyListsLiteralExpression(BaseExpression):
    """
    Helper type to represent a list literal containing only empty lists during parsing.
    This type should never be used during evaluation. After determining the concrete
    element type, this expression type must be replaced with a `ListLiteralExpression`
    with an explicit element type.
    """

    model_config = ConfigDict(frozen=True)
    expression_type: Literal[ExpressionType.LIST_OF_EMPTY_LISTS_LITERAL] = ExpressionType.LIST_OF_EMPTY_LISTS_LITERAL
    nested_empty_lists: list["ListOfEmptyListsLiteralExpression"]  # Empty if this is an empty list literal by itself.

    @override
    def get_data_type(self) -> DataType:
        raise ExecutionError("Unable to deduce type of empty list literal.")

    @override
    async def evaluate(
        self,
        context: ExecutionContext,
    ) -> Value:
        raise AssertionError("List of empty lists literal must not be used directly without specifying element type.")


@final
class ListLiteralExpression(BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.LIST_LITERAL] = ExpressionType.LIST_LITERAL
    elements: "list[Expression]"
    element_type: DataType

    @override
    def get_data_type(self) -> DataType:
        return ListType(of_type=self.element_type)

    @override
    async def evaluate(
        self,
        context: ExecutionContext,
    ) -> Value:
        return ListValue(
            element_type=self.element_type,
            elements=[await element.evaluate(context) for element in self.elements],
        )


@final
class SubscriptOperationExpression(BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.SUBSCRIPT_OPERATION] = ExpressionType.SUBSCRIPT_OPERATION
    operand: "Expression"
    index: "Expression"
    data_type: DataType

    @override
    def get_data_type(self) -> DataType:
        return self.data_type

    @override
    async def evaluate(
        self,
        context: ExecutionContext,
    ) -> Value:
        operand_value: Final = await self.operand.evaluate(context)
        index_value: Final = await self.index.evaluate(context)
        match operand_value, index_value:
            case (StringValue(value=s), NumberValue(value=i)):
                if not i.is_integer():
                    msg = f"String index must be an integer, got non-integer {i}"
                    raise ExecutionError(msg)
                int_index = int(i)
                if int_index not in range(len(s)):
                    msg = f"String index {int_index} out of range for string of length {len(s)}"
                    raise ExecutionError(msg)
                return StringValue(value=s[int_index])
            case (ListValue(elements=elements), NumberValue(value=i)):
                if not i.is_integer():
                    msg = f"List index must be an integer, got non-integer {i}"
                    raise ExecutionError(msg)
                int_index = int(i)
                if int_index not in range(len(elements)):
                    msg = f"List index {int_index} out of range for list of length {len(elements)}"
                    raise ExecutionError(msg)
                return elements[int_index]
            case _, _:
                msg = (
                    f"Subscript operation not supported for operand type '{operand_value.get_data_type()}' "
                    + f"and index type '{index_value.get_data_type()}'"
                )
                raise ExecutionError(msg)


@final
class ListComprehensionExpression(BaseExpression):
    """
    Expression of the form `for <iterable> as <element> yield <expression>`, where `<iterable>`
    can either be a list or a string. The type of `<element>` is determined by the type of
    elements in `<iterable>`, and the type of the whole expression is a list of the type of
    `<expression>`.
    Evaluating the expression does not open a scope; however, the variable named `<element>`
    is not allowed to shadow any existing variable in the context. Therefore, the expression
    acts *as if* it opened a new scope for the variable. The shadowing is prevented by the
    parser.
    """

    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.LIST_COMPREHENSION] = ExpressionType.LIST_COMPREHENSION
    iterable: "Expression"
    element_variable_name: str
    condition: Optional["Expression"]
    expression: "Expression"

    @override
    def get_data_type(self) -> DataType:
        return ListType(of_type=self.expression.get_data_type())

    @override
    async def evaluate(
        self,
        context: ExecutionContext,
    ) -> Value:
        iterable_value: Final = await self.iterable.evaluate(context)
        elements: Final[list[Value]] = []
        match iterable_value:
            case StringValue(value=s):
                for char in s:
                    context.variables[self.element_variable_name] = StringValue(value=char)
                    if self.condition is None or await self.condition.evaluate(context) == BoolValue(value=True):
                        element_value = await self.expression.evaluate(context)
                        elements.append(element_value)
            case ListValue(elements=iterable_elements):
                for item in iterable_elements:
                    context.variables[self.element_variable_name] = item
                    if self.condition is None or await self.condition.evaluate(context) == BoolValue(value=True):
                        element_value = await self.expression.evaluate(context)
                        elements.append(element_value)
            case _:
                msg = f"List comprehension iterable must be a string or a list, got {iterable_value.get_data_type()}"
                raise ExecutionError(msg)
        return ListValue(
            element_type=self.expression.get_data_type(),
            elements=elements,
        )


@final
class FoldExpression(BaseExpression):
    """
    Expression of the form `fold <iterable> as <accumulator>, <element> with <expression>`,
    where `<iterable>` can either be a list or a string. The types of `<accumulator>`, `<element>`, and
    `<expression>` have to be identical and are determined by the type of `<iterable>`. This is
    already checked by the parser.
    """

    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.FOLD] = ExpressionType.FOLD
    iterable: "Expression"
    accumulator_variable_name: str
    element_variable_name: str
    expression: "Expression"

    @override
    def get_data_type(self) -> DataType:
        return self.expression.get_data_type()

    @override
    async def evaluate(
        self,
        context: ExecutionContext,
    ) -> Value:
        iterable_value: Final = await self.iterable.evaluate(context)
        match iterable_value:
            case StringValue(value=s):
                string_accumulator = StringValue(value="")
                for char in s:
                    context.variables[self.accumulator_variable_name] = string_accumulator
                    context.variables[self.element_variable_name] = StringValue(value=char)
                    string_accumulator = await self.expression.evaluate(context)
                return string_accumulator
            case ListValue(elements=iterable_elements):
                if not iterable_elements:
                    msg = "Fold expression iterable must not be empty."
                    raise ExecutionError(msg)
                list_accumulator = iterable_elements[0]
                for item in iterable_elements[1:]:
                    context.variables[self.accumulator_variable_name] = list_accumulator
                    context.variables[self.element_variable_name] = item
                    list_accumulator = await self.expression.evaluate(context)
                return list_accumulator
            case _:
                msg = f"Fold expression iterable must be a string or a list, got {iterable_value.get_data_type()}"
                raise ExecutionError(msg)


@final
class SplitExpression(BaseExpression):
    """
    Expression of the form `split(<string>)` or `split(<string>, <delimiter>)`.
    Splits the string by the delimiter (or by space if no delimiter is provided).
    Always returns a `list<string>`.
    """

    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.SPLIT_OPERATION] = ExpressionType.SPLIT_OPERATION
    string_expression: "Expression"
    delimiter_expression: Optional["Expression"]

    @override
    def get_data_type(self) -> DataType:
        return ListType(of_type=StringType())

    @override
    async def evaluate(
        self,
        context: ExecutionContext,
    ) -> Value:
        string_value: Final = await self.string_expression.evaluate(context)
        if not isinstance(string_value, StringValue):
            msg = f"split() requires a string as first argument, got '{string_value.get_data_type()}'"
            raise ExecutionError(msg)

        delimiter = " "
        if self.delimiter_expression is not None:
            delimiter_value: Final = await self.delimiter_expression.evaluate(context)
            if not isinstance(delimiter_value, StringValue):
                msg = f"split() requires a string as delimiter argument, got '{delimiter_value.get_data_type()}'"
                raise ExecutionError(msg)
            delimiter = delimiter_value.value

        parts = string_value.value.split(delimiter)
        return ListValue(
            elements=[StringValue(value=part) for part in parts],
            element_type=StringType(),
        )


class JoinExpression(BaseExpression):
    """
    Expression of the form `join(<list<string>>)` or `join(<list<string>>, <delimiter>)`.
    Joins the list of strings with the delimiter (or with no separator if no delimiter is provided).
    Always returns a `string`.
    """

    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.JOIN_OPERATION] = ExpressionType.JOIN_OPERATION
    list_expression: "Expression"
    delimiter_expression: Optional["Expression"]

    @override
    def get_data_type(self) -> DataType:
        return StringType()

    @override
    async def evaluate(
        self,
        context: ExecutionContext,
    ) -> Value:
        list_value: Final = await self.list_expression.evaluate(context)
        if not isinstance(list_value, ListValue):
            msg = f"join() requires a list as first argument, got '{list_value.get_data_type()}'"
            raise ExecutionError(msg)

        # Verify all elements are strings
        string_elements: list[StringValue] = []
        for element in list_value.elements:
            if not isinstance(element, StringValue):
                msg = f"join() requires a list of strings, got list containing '{element.get_data_type()}'"
                raise ExecutionError(msg)
            string_elements.append(element)

        delimiter = ""
        if self.delimiter_expression is not None:
            delimiter_value: Final = await self.delimiter_expression.evaluate(context)
            if not isinstance(delimiter_value, StringValue):
                msg = f"join() requires a string as delimiter argument, got '{delimiter_value.get_data_type()}'"
                raise ExecutionError(msg)
            delimiter = delimiter_value.value

        string_parts = [element.value for element in string_elements]
        return StringValue(value=delimiter.join(string_parts))


class SortExpression(BaseExpression):
    """
    Expression of the form `sort(<list>)` or `sort(<list>; <lhs>, <rhs> yeet <comparison>)`.
    For list<number>, the comparison expression is optional and defaults to ascending numeric order.
    For other list types, a custom comparison expression is required.
    The comparison expression should evaluate to true if lhs < rhs.
    Returns a sorted list of the same type.
    """

    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.SORT_OPERATION] = ExpressionType.SORT_OPERATION
    list_expression: "Expression"
    lhs_variable_name: Optional[str]
    rhs_variable_name: Optional[str]
    comparison_expression: Optional["Expression"]

    @override
    def get_data_type(self) -> DataType:
        return self.list_expression.get_data_type()

    @override
    async def evaluate(
        self,
        context: ExecutionContext,
    ) -> Value:
        list_value: Final = await self.list_expression.evaluate(context)
        if not isinstance(list_value, ListValue):
            msg = f"sort() requires a list, got '{list_value.get_data_type()}'"
            raise ExecutionError(msg)

        if len(list_value.elements) <= 1:
            # Already sorted
            return list_value

        # If no comparison expression, use default numeric comparison for list<number>
        if self.comparison_expression is None:
            # Default sort for numbers (ascending)
            def numeric_compare(lhs: Value, rhs: Value) -> int:
                if not isinstance(lhs, NumberValue) or not isinstance(rhs, NumberValue):
                    msg = "Default sort requires numeric values"
                    raise ExecutionError(msg)
                if lhs.value < rhs.value:
                    return -1
                if lhs.value > rhs.value:
                    return 1
                return 0

            # Use merge sort with numeric comparison
            def sync_merge_sort(elements: list[Value]) -> list[Value]:
                if len(elements) <= 1:
                    return elements

                mid = len(elements) // 2
                left = sync_merge_sort(elements[:mid])
                right = sync_merge_sort(elements[mid:])

                result: list[Value] = []
                i = 0
                j = 0

                while i < len(left) and j < len(right):
                    if numeric_compare(left[i], right[j]) <= 0:
                        result.append(left[i])
                        i += 1
                    else:
                        result.append(right[j])
                        j += 1

                result.extend(left[i:])
                result.extend(right[j:])
                return result

            sorted_elements = sync_merge_sort(list_value.elements)
            return ListValue(elements=sorted_elements, element_type=list_value.element_type)

        # Custom comparison expression provided
        async def compare(lhs: Value, rhs: Value) -> int:
            if self.lhs_variable_name is None or self.rhs_variable_name is None or self.comparison_expression is None:
                msg = "Variable names and comparison expression required for custom comparison"
                raise ExecutionError(msg)
            context.variables[self.lhs_variable_name] = lhs
            context.variables[self.rhs_variable_name] = rhs
            result: Final = await self.comparison_expression.evaluate(context)
            if not isinstance(result, BoolValue):
                msg = f"sort() comparison expression must return a bool, got '{result.get_data_type()}'"
                raise ExecutionError(msg)

            # If lhs < rhs returns True, then lhs should come before rhs
            if result.value:
                return -1

            # Check if rhs < lhs (to determine if they're equal or rhs comes first)
            context.variables[self.lhs_variable_name] = rhs
            context.variables[self.rhs_variable_name] = lhs
            reverse_result: Final = await self.comparison_expression.evaluate(context)
            if not isinstance(reverse_result, BoolValue):
                msg = f"sort() comparison expression must return a bool, got '{reverse_result.get_data_type()}'"
                raise ExecutionError(msg)

            if reverse_result.value:
                return 1
            return 0

        # Use merge sort for O(n log n) performance with async comparison
        async def async_merge_sort(elements: list[Value]) -> list[Value]:
            if len(elements) <= 1:
                return elements

            # Divide
            mid = len(elements) // 2
            left = await async_merge_sort(elements[:mid])
            right = await async_merge_sort(elements[mid:])

            # Conquer (merge)
            result: list[Value] = []
            i = 0
            j = 0

            while i < len(left) and j < len(right):
                cmp_result = await compare(left[i], right[j])
                if cmp_result <= 0:
                    result.append(left[i])
                    i += 1
                else:
                    result.append(right[j])
                    j += 1

            # Append remaining elements
            result.extend(left[i:])
            result.extend(right[j:])
            return result

        sorted_elements = await async_merge_sort(list_value.elements)
        return ListValue(elements=sorted_elements, element_type=list_value.element_type)


type Expression = Annotated[
    StringLiteralExpression
    | NumberLiteralExpression
    | BoolLiteralExpression
    | StoreIdentifierExpression
    | ParameterIdentifierExpression
    | VariableIdentifierExpression
    | UnaryOperationExpression
    | BinaryOperationExpression
    | TernaryOperationExpression
    | CallOperationExpression
    | ListOfEmptyListsLiteralExpression
    | ListLiteralExpression
    | SubscriptOperationExpression
    | ListComprehensionExpression
    | FoldExpression
    | SplitExpression
    | JoinExpression
    | SortExpression,
    Discriminator("expression_type"),
]


# Rebuild all models because of forward references.
StringLiteralExpression.model_rebuild()
NumberLiteralExpression.model_rebuild()
BoolLiteralExpression.model_rebuild()
StoreIdentifierExpression.model_rebuild()
ParameterIdentifierExpression.model_rebuild()
VariableIdentifierExpression.model_rebuild()
UnaryOperationExpression.model_rebuild()
BinaryOperationExpression.model_rebuild()
TernaryOperationExpression.model_rebuild()
CallOperationExpression.model_rebuild()
SubscriptOperationExpression.model_rebuild()
ListOfEmptyListsLiteralExpression.model_rebuild()
ListComprehensionExpression.model_rebuild()
FoldExpression.model_rebuild()
SplitExpression.model_rebuild()
JoinExpression.model_rebuild()
SortExpression.model_rebuild()
