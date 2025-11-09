from typing import Final
from typing import Optional
from typing import final

from chatbot2k.scripting_engine.stores import BasicPersistentStore
from chatbot2k.scripting_engine.stores import StoreKey
from chatbot2k.scripting_engine.types.value import Value


@final
class MockStore(BasicPersistentStore):
    def __init__(self, initial_data: Optional[dict[StoreKey, Value]] = None) -> None:
        self._data: Final[dict[StoreKey, Value]] = {} if initial_data is None else initial_data

    def read_values(self, keys: set[StoreKey]) -> dict[StoreKey, Value]:
        return {key: self._data[key] for key in keys if key in self._data}

    def store_values(self, values: dict[StoreKey, Value]) -> None:
        self._data.update(values)
