from typing import Final
from typing import Optional

from chatbot2k.scripting_engine.lexer import Lexer
from chatbot2k.scripting_engine.parser import Parser
from chatbot2k.scripting_engine.stores import StoreKey
from chatbot2k.scripting_engine.types.value import Value
from test.mock_store import MockStore


def _execute(source: str, store_overrides: Optional[dict[str, Value]] = None) -> Optional[str]:
    lexer: Final = Lexer(source)
    tokens: Final = lexer.tokenize()
    script_name: Final = "!test-script"
    parser: Final = Parser(script_name, tokens)
    script: Final = parser.parse()

    initial_data: Final[dict[StoreKey, Value]] = {}
    for store in script.stores:
        key = StoreKey(script_name, store.name)
        value = store.value.evaluate(script_name, initial_data, {})
        initial_data[key] = value

    if store_overrides is not None:
        initial_data.update({StoreKey(script_name, store_name): value for store_name, value in store_overrides.items()})

    return script.execute(MockStore(initial_data))


def test_hello_world() -> None:
    output: Final = _execute("PRINT 'Hello, world!';")
    assert output == "Hello, world!"


def test_counter() -> None:
    output: Final = _execute("STORE counter = 0; counter = counter + 1; PRINT counter;")
    assert output == "1"


def test_calculation() -> None:
    output: Final = _execute("STORE a = 40; PRINT a + 2;")
    assert output == "42"
