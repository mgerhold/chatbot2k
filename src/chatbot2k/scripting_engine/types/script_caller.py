from typing import Protocol
from typing import runtime_checkable


@runtime_checkable
class ScriptCaller(Protocol):
    async def __call__(self, script_name: str, *args: str) -> str: ...
