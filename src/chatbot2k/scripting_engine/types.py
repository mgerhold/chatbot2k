from abc import ABC
from abc import abstractmethod
from enum import StrEnum
from typing import Annotated
from typing import Final
from typing import Literal
from typing import Self
from typing import final
from typing import override

from pydantic.config import ConfigDict
from pydantic.functional_validators import AfterValidator
from pydantic.main import BaseModel
from pydantic.types import Discriminator


@final
class DataType(StrEnum):
    NUMBER = "number"
    STRING = "string"


@final
class Store(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    value: "Expression"

    @property
    def data_type(self) -> DataType:
        return self.value.get_data_type()


@final
class ExpressionType(StrEnum):
    STRING_LITERAL = "string_literal"
    NUMBER_LITERAL = "number_literal"
    STORE_IDENTIFIER = "store_identifier"
    VARIABLE_IDENTIFIER = "variable_identifier"
    UNARY_OPERATION = "unary_operation"
    BINARY_OPERATION = "binary_operation"


class BaseExpression(ABC):
    @abstractmethod
    def get_data_type(self) -> DataType: ...


@final
class StringLiteralExpression(BaseModel, BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.STRING_LITERAL] = ExpressionType.STRING_LITERAL
    value: str

    @override
    def get_data_type(self) -> DataType:
        return DataType.STRING

    @classmethod
    def from_lexeme(cls, lexeme: str) -> Self:
        if not lexeme.startswith("'") or not lexeme.endswith("'"):
            msg = f"Invalid string lexeme: {lexeme}"
            raise AssertionError(msg)
        escaped_string = ""

        i = 1
        while i < len(lexeme) - 1:
            current = lexeme[i]
            next_ = lexeme[i + 1]
            match current, next_:
                case "\\", "n":
                    escaped_string += "\n"
                    i += 2
                case "\\", "'":
                    escaped_string += "'"
                    i += 2
                case "\\", _:
                    msg = f"Invalid escape sequence: \\{next_}"
                    raise AssertionError(msg)
                case _, _:
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


@final
class StoreIdentifierExpression(BaseModel, BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.STORE_IDENTIFIER] = ExpressionType.STORE_IDENTIFIER
    store_name: str
    data_type: DataType

    @override
    def get_data_type(self) -> DataType:
        return self.data_type


@final
class VariableIdentifierExpression(BaseModel, BaseExpression):
    model_config = ConfigDict(frozen=True)

    expression_type: Literal[ExpressionType.VARIABLE_IDENTIFIER] = ExpressionType.VARIABLE_IDENTIFIER
    variable_name: str
    data_type: DataType

    @override
    def get_data_type(self) -> DataType:
        return self.data_type


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


type Expression = Annotated[
    StringLiteralExpression
    | NumberLiteralExpression
    | StoreIdentifierExpression
    | VariableIdentifierExpression
    | UnaryOperationExpression
    | BinaryOperationExpression,
    Discriminator("expression_type"),
]


@final
class StatementKind(StrEnum):
    PRINT = "print"
    ASSIGNMENT = "assignment"
    VARIABLE_DEFINITION = "variable_definition"


@final
class PrintStatement(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[StatementKind.PRINT] = StatementKind.PRINT
    argument: Expression


@final
class AssignmentStatement(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[StatementKind.ASSIGNMENT] = StatementKind.ASSIGNMENT
    assignment_target: StoreIdentifierExpression | VariableIdentifierExpression
    expression: Expression  # The rvalue.


@final
class VariableDefinitionStatement(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[StatementKind.VARIABLE_DEFINITION] = StatementKind.VARIABLE_DEFINITION
    variable_name: str
    data_type: DataType
    initial_value: Expression


type Statement = Annotated[
    PrintStatement | AssignmentStatement | VariableDefinitionStatement,
    Discriminator("kind"),
]


def is_not_empty[T](values: list[T]) -> list[T]:
    if not values:
        raise ValueError("List must not be empty")
    return values


@final
class Script(BaseModel):
    model_config = ConfigDict(frozen=True)

    stores: list[Store]  # Maybe empty.
    statements: Annotated[list[Statement], AfterValidator(is_not_empty)]
