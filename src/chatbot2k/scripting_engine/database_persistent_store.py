import json
from typing import Annotated
from typing import Final
from typing import final
from typing import override

from pydantic import Discriminator
from pydantic import TypeAdapter

from chatbot2k.database.engine import Database
from chatbot2k.scripting_engine.stores import BasicPersistentStore
from chatbot2k.scripting_engine.stores import StoreKey
from chatbot2k.scripting_engine.types.value import NumberValue
from chatbot2k.scripting_engine.types.value import StringValue
from chatbot2k.scripting_engine.types.value import Value


@final
class DatabasePersistentStore(BasicPersistentStore):
    """Persistent store implementation that uses the database to persist script store values."""

    def __init__(self, database: Database) -> None:
        self._database: Final = database
        # Use the union type directly for TypeAdapter. This is necessary to satisfy Pyright.
        self._value_adapter: Final[TypeAdapter[Annotated[NumberValue | StringValue, Discriminator("kind")]]] = (
            TypeAdapter(Annotated[NumberValue | StringValue, Discriminator("kind")])
        )

    @override
    def read_values(self, keys: set[StoreKey]) -> dict[StoreKey, Value]:
        """Read store values from the database for the given keys."""
        result: Final[dict[StoreKey, Value]] = {}

        for key in keys:
            store = self._database.get_script_store(
                script_command=key.script_name,
                store_name=key.store_name,
            )

            if store is not None:
                # Deserialize the value from JSON.
                value_dict = json.loads(store.value_json)
                result[key] = self._value_adapter.validate_python(value_dict)

        return result

    @override
    def store_values(self, values: dict[StoreKey, Value]) -> None:
        """Store values to the database."""
        for key, value in values.items():
            # Serialize the value to JSON.
            value_json = value.model_dump_json()

            # Update the store in the database.
            self._database.update_script_store_value(
                script_command=key.script_name,
                store_name=key.store_name,
                value_json=value_json,
            )
