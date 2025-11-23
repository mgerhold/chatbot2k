from abc import ABC
from abc import abstractmethod
from enum import StrEnum
from typing import Annotated
from typing import Final
from typing import Literal
from typing import Self
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
from chatbot2k.scripting_engine.types.data_types import DataType
from chatbot2k.scripting_engine.types.execution_context import ExecutionContext
from chatbot2k.scripting_engine.types.execution_error import ExecutionError
from chatbot2k.scripting_engine.types.value import BoolValue
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
    SUBSCRIPT_OPERATION = "subscript_operation"


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
        return DataType.STRING

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
        return DataType.NUMBER

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
        return DataType.BOOL

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
        return DataType.STRING

    @override
    async def evaluate(
        self,
        context: ExecutionContext,
    ) -> Value:
        value: Final = context.parameters.get(self.parameter_name)
        if value is None:
            msg = f"Parameter '{self.parameter_name}' not defined."
            raise ExecutionError(msg)
        if value.get_data_type() != DataType.STRING:
            msg = (
                f"Type mismatch when accessing parameter '{self.parameter_name}': "
                + f"expected {DataType.STRING}, got {value.get_data_type()}"
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

    EQUALS = "=="
    NOT_EQUALS = "!="
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="

    AND = "and"
    OR = "or"


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
            case (UnaryOperator.PLUS | UnaryOperator.NEGATE, DataType.NUMBER):
                return DataType.NUMBER
            case (UnaryOperator.NOT, DataType.BOOL):
                return DataType.BOOL
            case (UnaryOperator.TO_NUMBER, DataType.BOOL | DataType.NUMBER | DataType.STRING):
                return DataType.NUMBER
            case (UnaryOperator.TO_STRING, DataType.BOOL | DataType.NUMBER | DataType.STRING):
                return DataType.STRING
            case (UnaryOperator.TO_BOOL, DataType.BOOL | DataType.NUMBER | DataType.STRING):
                return DataType.BOOL
            case (UnaryOperator.EVALUATE, DataType.STRING):
                return DataType.STRING
            case (
                UnaryOperator.PLUS
                | UnaryOperator.NEGATE
                | UnaryOperator.TO_NUMBER
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
                (DataType.BOOL, BinaryOperator.EQUALS, DataType.BOOL)
                | (DataType.BOOL, BinaryOperator.NOT_EQUALS, DataType.BOOL)
                | (DataType.NUMBER, BinaryOperator.EQUALS, DataType.NUMBER)
                | (DataType.NUMBER, BinaryOperator.NOT_EQUALS, DataType.NUMBER)
                | (DataType.NUMBER, BinaryOperator.LESS_THAN, DataType.NUMBER)
                | (DataType.NUMBER, BinaryOperator.LESS_THAN_OR_EQUAL, DataType.NUMBER)
                | (DataType.NUMBER, BinaryOperator.GREATER_THAN, DataType.NUMBER)
                | (DataType.NUMBER, BinaryOperator.GREATER_THAN_OR_EQUAL, DataType.NUMBER)
                | (DataType.STRING, BinaryOperator.EQUALS, DataType.STRING)
                | (DataType.STRING, BinaryOperator.NOT_EQUALS, DataType.STRING)
                | (DataType.STRING, BinaryOperator.LESS_THAN, DataType.STRING)
                | (DataType.STRING, BinaryOperator.LESS_THAN_OR_EQUAL, DataType.STRING)
                | (DataType.STRING, BinaryOperator.GREATER_THAN, DataType.STRING)
                | (DataType.STRING, BinaryOperator.GREATER_THAN_OR_EQUAL, DataType.STRING)
            ):
                return DataType.BOOL
            case (DataType.BOOL, BinaryOperator.AND, DataType.BOOL) | (DataType.BOOL, BinaryOperator.OR, DataType.BOOL):
                return DataType.BOOL
            case (
                (DataType.NUMBER, BinaryOperator.ADD, DataType.NUMBER)
                | (DataType.NUMBER, BinaryOperator.SUBTRACT, DataType.NUMBER)
                | (DataType.NUMBER, BinaryOperator.MULTIPLY, DataType.NUMBER)
                | (DataType.NUMBER, BinaryOperator.DIVIDE, DataType.NUMBER)
            ):
                return DataType.NUMBER
            case (DataType.STRING, BinaryOperator.ADD, DataType.STRING):
                return DataType.STRING
            case (DataType.NUMBER, _, _) | (_, _, DataType.NUMBER):
                msg = f"Operator {self.operator} is not supported for number operands"
                raise TypeError(msg)
            case (DataType.STRING, _, _) | (_, _, DataType.STRING):
                msg = f"Operator {self.operator} is not supported for string operands"
                raise TypeError(msg)
            # TODO: Create minimal example and file a Pyright issue about this false positive.
            case (DataType.BOOL, _, _) | (_, _, DataType.BOOL):  # type: ignore[reportUnnecessaryComparison]
                msg = f"Operator {self.operator} is not supported for boolean operands"
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
            case StringValue(value=l), BinaryOperator.ADD, StringValue(value=r):
                return StringValue(value=l + r)
            case _, _, _:
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
        if predicate.get_data_type() != DataType.BOOL:
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
        return DataType.STRING

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
                int_index: Final = int(i)
                if int_index not in range(len(s)):
                    msg = f"String index {int_index} out of range for string of length {len(s)}"
                    raise ExecutionError(msg)
                return StringValue(value=s[int_index])
            case _, _:
                msg = (
                    f"Subscript operation not supported for operand type '{operand_value.get_data_type()}' "
                    + f"and index type '{index_value.get_data_type()}'"
                )
                raise ExecutionError(msg)


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
    | SubscriptOperationExpression,
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
