from typing import Annotated
from typing import Final
from typing import Optional
from typing import final

from pydantic import AfterValidator
from pydantic import BaseModel
from pydantic import ConfigDict

from chatbot2k.scripting_engine.stores import BasicPersistentStore
from chatbot2k.scripting_engine.stores import StoreKey
from chatbot2k.scripting_engine.types.data_types import DataType
from chatbot2k.scripting_engine.types.expressions import Expression
from chatbot2k.scripting_engine.types.statements import Statement
from chatbot2k.scripting_engine.types.statements import is_not_empty
from chatbot2k.scripting_engine.types.value import Value


@final
class Store(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    value: Expression

    @property
    def data_type(self) -> DataType:
        return self.value.get_data_type()


@final
class Script(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str  # Usually the name of the command, e.g. "!run".
    stores: list[Store]  # Maybe empty.
    statements: Annotated[list[Statement], AfterValidator(is_not_empty)]

    def execute(self, persistent_store: BasicPersistentStore) -> Optional[str]:
        stores: Final = persistent_store.read_values(self._collect_required_stores())
        variables: Final[dict[str, Value]] = {}
        output: Optional[str] = None
        for statement in self.statements:
            if (result := statement.execute(self.name, stores, variables)) is not None:
                output = result if output is None else f"{output}{result}"
        return output

    def _collect_required_stores(self) -> set[StoreKey]:
        required_stores: Final[set[StoreKey]] = set()
        for store in self.stores:
            required_stores.add(StoreKey(script_name=self.name, store_name=store.name))
        # TODO: As soon as we support fetching stored values from other scripts, we need to
        #       iterate over all statements and collect the store identifiers used there as well.
        return required_stores
