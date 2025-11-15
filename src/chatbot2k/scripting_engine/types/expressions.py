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
from chatbot2k.scripting_engine.stores import StoreKey
from chatbot2k.scripting_engine.types.data_types import DataType
from chatbot2k.scripting_engine.types.execution_error import ExecutionError
from chatbot2k.scripting_engine.types.value import NumberValue
from chatbot2k.scripting_engine.types.value import StringValue
from chatbot2k.scripting_engine.types.value import Value


@final
class ExpressionType(StrEnum):
    STRING_LITERAL = "string_literal"
    NUMBER_LITERAL = "number_literal"
    STORE_IDENTIFIER = "store_identifier"
    PARAMETER_IDENTIFIER = "parameter_identifier"
    VARIABLE_IDENTIFIER = "variable_identifier"
    UNARY_OPERATION = "unary_operation"
    BINARY_OPERATION = "binary_operation"


class BaseExpression(ABC):
    @abstractmethod
    def get_data_type(self) -> DataType: ...

    @abstractmethod
    def evaluate(
        self,
        script_name: str,
        stores: dict[StoreKey, Value],
        parameters: dict[str, Value],
        variables: dict[str, Value],
    ) -> Value: ...


@final
class StringLiteralExpression(BaseModel, BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.STRING_LITERAL] = ExpressionType.STRING_LITERAL
    value: str

    @override
    def get_data_type(self) -> DataType:
        return DataType.STRING

    @override
    def evaluate(
        self,
        script_name: str,
        stores: dict[StoreKey, Value],
        parameters: dict[str, Value],
        variables: dict[str, Value],
    ) -> Value:
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
class NumberLiteralExpression(BaseModel, BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.NUMBER_LITERAL] = ExpressionType.NUMBER_LITERAL
    value: float

    @override
    def get_data_type(self) -> DataType:
        return DataType.NUMBER

    @override
    def evaluate(
        self,
        script_name: str,
        stores: dict[StoreKey, Value],
        parameters: dict[str, Value],
        variables: dict[str, Value],
    ) -> Value:
        return NumberValue(value=self.value)


@final
class StoreIdentifierExpression(BaseModel, BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.STORE_IDENTIFIER] = ExpressionType.STORE_IDENTIFIER
    store_name: str
    data_type: DataType

    @override
    def get_data_type(self) -> DataType:
        return self.data_type

    @override
    def evaluate(
        self,
        script_name: str,
        stores: dict[StoreKey, Value],
        parameters: dict[str, Value],
        variables: dict[str, Value],
    ) -> Value:
        store_key: Final = StoreKey(
            script_name=script_name,
            store_name=self.store_name,
        )
        value: Final = stores.get(store_key)
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
class ParameterIdentifierExpression(BaseModel, BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.PARAMETER_IDENTIFIER] = ExpressionType.PARAMETER_IDENTIFIER
    parameter_name: str

    @override
    def get_data_type(self) -> DataType:
        # All parameters are strings.
        return DataType.STRING

    @override
    def evaluate(
        self,
        script_name: str,
        stores: dict[StoreKey, Value],
        parameters: dict[str, Value],
        variables: dict[str, Value],
    ) -> Value:
        value: Final = parameters.get(self.parameter_name)
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
class VariableIdentifierExpression(BaseModel, BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.VARIABLE_IDENTIFIER] = ExpressionType.VARIABLE_IDENTIFIER
    variable_name: str
    data_type: DataType

    @override
    def get_data_type(self) -> DataType:
        return self.data_type

    @override
    def evaluate(
        self,
        script_name: str,
        stores: dict[StoreKey, Value],
        parameters: dict[str, Value],
        variables: dict[str, Value],
    ) -> Value:
        value: Final = variables.get(self.variable_name)
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


@final
class UnaryOperator(StrEnum):
    PLUS = "+"
    NEGATE = "-"


@final
class UnaryOperationExpression(BaseModel, BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.UNARY_OPERATION] = ExpressionType.UNARY_OPERATION
    operator: UnaryOperator
    operand: "Expression"

    @override
    def get_data_type(self) -> DataType:
        operand_type: Final = self.operand.get_data_type()
        if operand_type == DataType.NUMBER:
            return DataType.NUMBER
        msg: Final = f"Unary operator {self.operator} is not supported for {operand_type} operands"
        raise TypeError(msg)

    @override
    def evaluate(
        self,
        script_name: str,
        stores: dict[StoreKey, Value],
        parameters: dict[str, Value],
        variables: dict[str, Value],
    ) -> Value:
        operand_value: Final = self.operand.evaluate(script_name, stores, parameters, variables)
        match self.operator, operand_value:
            case UnaryOperator.PLUS, NumberValue(value=v):
                return NumberValue(value=v)
            case UnaryOperator.NEGATE, NumberValue(value=v):
                return NumberValue(value=-v)
            case _, _:
                msg: Final = (
                    f"Unary operator {self.operator} is not supported for {operand_value.get_data_type()} operands"
                )
                raise ExecutionError(msg)


@final
class BinaryOperationExpression(BaseModel, BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.BINARY_OPERATION] = ExpressionType.BINARY_OPERATION
    left: "Expression"
    operator: BinaryOperator
    right: "Expression"

    @override
    def get_data_type(self) -> DataType:
        match self.left.get_data_type(), self.operator, self.right.get_data_type():
            case (
                (DataType.NUMBER, BinaryOperator.ADD, DataType.NUMBER)
                | (DataType.NUMBER, BinaryOperator.SUBTRACT, DataType.NUMBER)
                | (DataType.NUMBER, BinaryOperator.MULTIPLY, DataType.NUMBER)
                | (DataType.NUMBER, BinaryOperator.DIVIDE, DataType.NUMBER)
            ):
                return DataType.NUMBER
            case (DataType.STRING, BinaryOperator.ADD, DataType.STRING):
                return DataType.STRING
            case (DataType.STRING, _, DataType.STRING) | (DataType.STRING, _, _) | (_, _, DataType.STRING):
                msg = f"Operator {self.operator} is not supported for string operands"
                raise TypeError(msg)

    @override
    def evaluate(
        self,
        script_name: str,
        stores: dict[StoreKey, Value],
        parameters: dict[str, Value],
        variables: dict[str, Value],
    ) -> Value:
        left_value: Final = self.left.evaluate(script_name, stores, parameters, variables)
        right_value: Final = self.right.evaluate(script_name, stores, parameters, variables)
        match left_value, self.operator, right_value:
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
                msg = f"Operator {self.operator} is not supported for the given operand types"
                raise ExecutionError(msg)


type Expression = Annotated[
    StringLiteralExpression
    | NumberLiteralExpression
    | StoreIdentifierExpression
    | ParameterIdentifierExpression
    | VariableIdentifierExpression
    | UnaryOperationExpression
    | BinaryOperationExpression,
    Discriminator("expression_type"),
]
