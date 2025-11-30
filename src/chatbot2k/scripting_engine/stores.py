from abc import ABC
from abc import abstractmethod
from typing import NamedTuple
from typing import final

from chatbot2k.scripting_engine.types.value import Value


@final
class StoreKey(NamedTuple):
    script_name: str
    store_name: str


class BasicPersistentStore(ABC):
    @abstractmethod
    def read_values(self, keys: set[StoreKey]) -> dict[StoreKey, Value]: ...

    @abstractmethod
    def store_values(self, values: dict[StoreKey, Value]) -> None: ...


@final
class AlwaysEmptyPersistentStore(BasicPersistentStore):
    def read_values(self, keys: set[StoreKey]) -> dict[StoreKey, Value]:
        return {}

    def store_values(self, values: dict[StoreKey, Value]) -> None:
        pass
