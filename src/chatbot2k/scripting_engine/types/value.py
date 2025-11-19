from abc import ABC
from abc import abstractmethod
from enum import StrEnum
from typing import Annotated
from typing import Literal
from typing import final
from typing import override

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Discriminator

from chatbot2k.scripting_engine.types.data_types import DataType


@final
class ValueKind(StrEnum):
    NUMBER = "number"
    STRING = "string"
    BOOL = "bool"


class BasicValue(BaseModel, ABC):
    @abstractmethod
    def get_data_type(self) -> DataType: ...

    @abstractmethod
    def to_string(self) -> str: ...


@final
class NumberValue(BasicValue):
    model_config = ConfigDict(frozen=True)

    kind: Literal[ValueKind.NUMBER] = ValueKind.NUMBER
    value: float

    @override
    def get_data_type(self) -> DataType:
        return DataType.NUMBER

    @override
    def to_string(self) -> str:
        if self.value.is_integer():
            return str(int(self.value))
        return str(self.value)


@final
class StringValue(BasicValue):
    model_config = ConfigDict(frozen=True)

    kind: Literal[ValueKind.STRING] = ValueKind.STRING
    value: str

    @override
    def get_data_type(self) -> DataType:
        return DataType.STRING

    @override
    def to_string(self) -> str:
        return self.value


@final
class BoolValue(BasicValue):
    model_config = ConfigDict(frozen=True)

    kind: Literal[ValueKind.BOOL] = ValueKind.BOOL
    value: bool

    @override
    def get_data_type(self) -> DataType:
        return DataType.BOOL

    @override
    def to_string(self) -> str:
        return str(self.value).lower()


type Value = Annotated[NumberValue | StringValue | BoolValue, Discriminator("kind")]
