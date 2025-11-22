from typing import TYPE_CHECKING
from typing import Final
from typing import Protocol
from typing import final
from typing import runtime_checkable

from chatbot2k.scripting_engine.types.execution_error import ExecutionError

if TYPE_CHECKING:
    from chatbot2k.scripting_engine.types.expressions import Expression


@final
@runtime_checkable
class BuiltinFunction(Protocol):
    async def __call__(self, *args: "Expression") -> str: ...


async def type_(*args: "Expression") -> str:
    if len(args) != 1:
        msg = f"'type' expected 1 argument, got {len(args)}"
        raise ExecutionError(msg)
    expression = args[0]
    return expression.get_data_type().value


BUILTIN_FUNCTIONS: Final[dict[str, BuiltinFunction]] = {
    "type": type_,
}
