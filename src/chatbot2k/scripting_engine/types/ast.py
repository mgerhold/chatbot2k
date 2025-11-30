import logging
from typing import Annotated
from typing import Final
from typing import Optional
from typing import final

from pydantic import AfterValidator
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from chatbot2k.app_state import AppState
from chatbot2k.scripting_engine.stores import BasicPersistentStore
from chatbot2k.scripting_engine.stores import StoreKey
from chatbot2k.scripting_engine.types.data_types import DataType
from chatbot2k.scripting_engine.types.execution_context import ExecutionContext
from chatbot2k.scripting_engine.types.execution_error import ExecutionError
from chatbot2k.scripting_engine.types.expressions import Expression
from chatbot2k.scripting_engine.types.script_caller import ScriptCaller
from chatbot2k.scripting_engine.types.statements import Statement
from chatbot2k.scripting_engine.types.statements import is_not_empty
from chatbot2k.scripting_engine.types.value import StringValue
from chatbot2k.scripting_engine.types.value import Value

logger: Final = logging.getLogger(__name__)


@final
class Store(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    value: Expression

    @property
    def data_type(self) -> DataType:
        return self.value.get_data_type()


@final
class Parameter(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str


@final
class Script(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str  # Usually the name of the command, e.g. "!run".
    stores: Annotated[list[Store], Field(default_factory=list)]  # Maybe empty.
    parameters: Annotated[list[Parameter], Field(default_factory=list)]  # Maybe empty.
    statements: Annotated[list[Statement], AfterValidator(is_not_empty)]

    async def execute(
        self,
        persistent_store: BasicPersistentStore,
        arguments: list[str],
        call_script: ScriptCaller,
        app_state: AppState,
    ) -> Optional[str]:
        arity: Final = len(self.parameters)
        if len(arguments) != arity:
            msg: Final = f"Script '{self.name}' expects {arity} arguments, but got {len(arguments)}."
            raise ExecutionError(msg)
        parameters: Final[dict[str, Value]] = {
            parameter.name: StringValue(value=argument_value)
            for parameter, argument_value in zip(self.parameters, arguments, strict=True)
        }
        output: Optional[str] = None

        execution_context: Final = ExecutionContext(
            app_state=app_state,
            call_stack=[self.name],
            stores=persistent_store.read_values(self._collect_required_stores()),
            parameters=parameters,
            variables={},
            call_script=call_script,
        )
        for statement in self.statements:
            if (result := await statement.execute(execution_context)) is not None:
                output = result if output is None else f"{output}{result}"
        persistent_store.store_values(execution_context.stores)
        return output

    def _collect_required_stores(self) -> set[StoreKey]:
        required_stores: Final[set[StoreKey]] = set()
        for store in self.stores:
            required_stores.add(StoreKey(script_name=self.name, store_name=store.name))
        # TODO: As soon as we support fetching stored values from other scripts, we need to
        #       iterate over all statements and collect the store identifiers used there as well.
        return required_stores
