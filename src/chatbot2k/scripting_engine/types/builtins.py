from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Final
from typing import final
from typing import override

from chatbot2k.scripting_engine.types.execution_error import ExecutionError

if TYPE_CHECKING:
    from chatbot2k.scripting_engine.types.expressions import Expression


class BuiltinFunction(ABC):
    @property
    @abstractmethod
    def arity(self) -> int:
        """Return the number of arguments this builtin function expects."""
        ...

    @abstractmethod
    async def execute(self, *args: "Expression") -> str:
        """Execute the builtin function with the given arguments."""
        ...

    @final
    async def __call__(self, *args: "Expression") -> str:
        expected_arity: Final = self.arity
        actual_arity: Final = len(args)
        if actual_arity != expected_arity:
            msg: Final = f"Expected {expected_arity} argument(s), got {actual_arity}"
            raise ExecutionError(msg)
        return await self.execute(*args)


@final
class _TypeFunction(BuiltinFunction):
    @property
    @override
    def arity(self) -> int:
        return 1

    @override
    async def execute(self, *args: "Expression") -> str:
        assert len(args) == self.arity
        expression: Final = args[0]
        return expression.get_data_type().value


BUILTIN_FUNCTIONS: Final[dict[str, BuiltinFunction]] = {
    "type": _TypeFunction(),
}
