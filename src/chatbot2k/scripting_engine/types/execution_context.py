from typing import NamedTuple
from typing import final

from chatbot2k.scripting_engine.stores import StoreKey
from chatbot2k.scripting_engine.types.script_caller import ScriptCaller
from chatbot2k.scripting_engine.types.value import Value


@final
class ExecutionContext(NamedTuple):
    call_stack: list[str]
    stores: dict[StoreKey, Value]
    parameters: dict[str, Value]
    variables: dict[str, Value]
    call_script: ScriptCaller
