from abc import ABC
from abc import abstractmethod
from enum import StrEnum
from typing import Annotated
from typing import Final
from typing import Literal
from typing import Optional
from typing import final
from typing import override

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Discriminator

from chatbot2k.scripting_engine.stores import StoreKey
from chatbot2k.scripting_engine.types.data_types import DataType
from chatbot2k.scripting_engine.types.execution_error import ExecutionError
from chatbot2k.scripting_engine.types.expressions import Expression
from chatbot2k.scripting_engine.types.expressions import ParameterIdentifierExpression
from chatbot2k.scripting_engine.types.expressions import StoreIdentifierExpression
from chatbot2k.scripting_engine.types.expressions import VariableIdentifierExpression
from chatbot2k.scripting_engine.types.value import Value


class BaseStatement(ABC):
    @abstractmethod
    def execute(
        self,
        script_name: str,
        stores: dict[StoreKey, Value],
        parameters: dict[str, Value],
        variables: dict[str, Value],
    ) -> Optional[str]: ...


@final
class StatementKind(StrEnum):
    PRINT = "print"
    ASSIGNMENT = "assignment"
    VARIABLE_DEFINITION = "variable_definition"


@final
class PrintStatement(BaseModel, BaseStatement):
    model_config = ConfigDict(frozen=True)

    kind: Literal[StatementKind.PRINT] = StatementKind.PRINT
    argument: Expression

    @override
    def execute(
        self,
        script_name: str,
        stores: dict[StoreKey, Value],
        parameters: dict[str, Value],
        variables: dict[str, Value],
    ) -> Optional[str]:
        value: Final = self.argument.evaluate(script_name, stores, parameters, variables)
        return value.to_string()


@final
class AssignmentStatement(BaseModel, BaseStatement):
    model_config = ConfigDict(frozen=True)

    kind: Literal[StatementKind.ASSIGNMENT] = StatementKind.ASSIGNMENT
    assignment_target: StoreIdentifierExpression | ParameterIdentifierExpression | VariableIdentifierExpression
    expression: Expression  # The rvalue.

    @override
    def execute(
        self,
        script_name: str,
        stores: dict[StoreKey, Value],
        parameters: dict[str, Value],
        variables: dict[str, Value],
    ) -> Optional[str]:
        match self.assignment_target:
            case StoreIdentifierExpression(store_name=store_name):
                store_key: Final = StoreKey(
                    script_name=script_name,
                    store_name=store_name,
                )
                value = stores.get(store_key)
                if value is None:
                    msg = f"Store '{store_name}' not found in script '{script_name}'"
                    raise ExecutionError(msg)
                if value.get_data_type() != self.expression.get_data_type():
                    msg = (
                        f"Type mismatch when assigning to store '{store_name}': "
                        + f"expected {value.get_data_type()}, got {self.expression.get_data_type()}"
                    )
                    raise ExecutionError(msg)
                stores[store_key] = self.expression.evaluate(script_name, stores, parameters, variables)
                return None
            case ParameterIdentifierExpression(parameter_name=parameter_name):
                if parameter_name not in parameters:
                    msg = f"Parameter '{parameter_name}' not defined"
                    raise ExecutionError(msg)
                value = parameters[parameter_name]
                if value.get_data_type() != self.expression.get_data_type():
                    msg = (
                        f"Type mismatch when assigning to parameter '{parameter_name}': "
                        + f"expected {value.get_data_type()}, got {self.expression.get_data_type()}"
                    )
                    raise ExecutionError(msg)
                parameters[parameter_name] = self.expression.evaluate(script_name, stores, parameters, variables)
                print(f"Assigned '{parameters[parameter_name]}' to parameter {parameter_name}")
                return None
            case VariableIdentifierExpression(variable_name=variable_name):
                if variable_name not in variables:
                    msg = f"Variable '{variable_name}' not defined"
                    raise ExecutionError(msg)
                value = variables[variable_name]
                if value.get_data_type() != self.expression.get_data_type():
                    msg = (
                        f"Type mismatch when assigning to variable '{variable_name}': "
                        + f"expected {value.get_data_type()}, got {self.expression.get_data_type()}"
                    )
                    raise ExecutionError(msg)
                variables[variable_name] = self.expression.evaluate(script_name, stores, parameters, variables)
                return None


@final
class VariableDefinitionStatement(BaseModel, BaseStatement):
    model_config = ConfigDict(frozen=True)

    kind: Literal[StatementKind.VARIABLE_DEFINITION] = StatementKind.VARIABLE_DEFINITION
    variable_name: str
    data_type: DataType
    initial_value: Expression

    @override
    def execute(
        self,
        script_name: str,
        stores: dict[StoreKey, Value],
        parameters: dict[str, Value],
        variables: dict[str, Value],
    ) -> Optional[str]:
        if self.variable_name in variables:
            msg = f"Variable '{self.variable_name}' already defined"
            raise ExecutionError(msg)
        if self.initial_value.get_data_type() != self.data_type:
            msg = (
                f"Type mismatch when defining variable '{self.variable_name}': "
                + f"expected {self.data_type}, got {self.initial_value.get_data_type()}"
            )
            raise ExecutionError(msg)
        variables[self.variable_name] = self.initial_value.evaluate(script_name, stores, parameters, variables)
        return None


def is_not_empty[T](values: list[T]) -> list[T]:
    if not values:
        raise ValueError("List must not be empty")
    return values


type Statement = Annotated[
    PrintStatement | AssignmentStatement | VariableDefinitionStatement,
    Discriminator("kind"),
]
