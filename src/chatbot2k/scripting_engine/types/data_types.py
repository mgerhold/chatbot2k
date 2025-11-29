from abc import ABC
from abc import abstractmethod
from enum import StrEnum
from typing import Annotated
from typing import Literal
from typing import final
from typing import override

from pydantic import BaseModel
from pydantic import Discriminator


@final
class DataTypeKind(StrEnum):
    NUMBER = "number"
    STRING = "string"
    BOOL = "bool"
    LIST = "list"


class BaseDataType(BaseModel, ABC):
    @abstractmethod
    def __str__(self) -> str: ...

    @final
    def __repr__(self) -> str:
        return str(self)


@final
class NumberType(BaseDataType):
    kind: Literal[DataTypeKind.NUMBER] = DataTypeKind.NUMBER

    @override
    def __str__(self) -> str:
        return "number"


@final
class StringType(BaseDataType):
    kind: Literal[DataTypeKind.STRING] = DataTypeKind.STRING

    @override
    def __str__(self) -> str:
        return "string"


@final
class BoolType(BaseDataType):
    kind: Literal[DataTypeKind.BOOL] = DataTypeKind.BOOL

    @override
    def __str__(self) -> str:
        return "bool"


@final
class ListType(BaseDataType):
    kind: Literal[DataTypeKind.LIST] = DataTypeKind.LIST

    of_type: "DataType"

    @override
    def __str__(self) -> str:
        return f"list<{self.of_type}>"


type DataType = Annotated[
    NumberType | StringType | BoolType | ListType,
    Discriminator("kind"),
]

ListType.model_rebuild()
