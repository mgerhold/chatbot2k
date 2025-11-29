import re
from typing import Final
from typing import NamedTuple
from typing import Optional
from typing import final

import pytest

from chatbot2k.scripting_engine.lexer import Lexer
from chatbot2k.scripting_engine.parser import AssignmentTypeError
from chatbot2k.scripting_engine.parser import CollectExpressionTypeError
from chatbot2k.scripting_engine.parser import EmptyListLiteralAssignmentToNonListError
from chatbot2k.scripting_engine.parser import EmptyListLiteralWithoutTypeAnnotationError
from chatbot2k.scripting_engine.parser import ExpectedEmptyListLiteralError
from chatbot2k.scripting_engine.parser import InitializationTypeError
from chatbot2k.scripting_engine.parser import ListElementTypeMismatchError
from chatbot2k.scripting_engine.parser import NestedListComprehensionsWithoutParenthesesError
from chatbot2k.scripting_engine.parser import Parser
from chatbot2k.scripting_engine.parser import ParserTypeError
from chatbot2k.scripting_engine.parser import SubscriptOperatorTypeError
from chatbot2k.scripting_engine.parser import TypeNotCallableError
from chatbot2k.scripting_engine.parser import UnknownVariableError
from chatbot2k.scripting_engine.parser import VariableRedefinitionError
from chatbot2k.scripting_engine.parser import VariableShadowsParameterError
from chatbot2k.scripting_engine.parser import VariableShadowsStoreError
from chatbot2k.scripting_engine.stores import StoreKey
from chatbot2k.scripting_engine.types.ast import Script
from chatbot2k.scripting_engine.types.builtins import BUILTIN_FUNCTIONS
from chatbot2k.scripting_engine.types.builtins import _Variadic  # type: ignore[reportPrivateUsage]
from chatbot2k.scripting_engine.types.execution_context import ExecutionContext
from chatbot2k.scripting_engine.types.execution_error import ExecutionError
from chatbot2k.scripting_engine.types.script_caller import ScriptCaller
from chatbot2k.scripting_engine.types.value import NumberValue
from chatbot2k.scripting_engine.types.value import StringValue
from chatbot2k.scripting_engine.types.value import Value
from test.mock_store import MockStore


@final
class CallableScript(NamedTuple):
    script: Script
    store: MockStore


@final
class _Success(NamedTuple):
    output: str


@final
class _Error(NamedTuple):
    error_type: type[Exception]
    error_match: str


type _Result = _Success | _Error


async def _execute(
    source: str,
    store_overrides: Optional[dict[str, Value]] = None,
    callable_scripts: Optional[dict[str, CallableScript]] = None,
) -> Optional[str]:
    output, _ = await _execute_with_store(source, store_overrides, callable_scripts)
    return output


async def _extract_store_data_from_script(
    script_name: str,
    script: Script,
    call_script: ScriptCaller,
) -> dict[StoreKey, Value]:
    data: Final[dict[StoreKey, Value]] = {}
    for store in script.stores:
        key = StoreKey(script_name, store.name)
        value = await store.value.evaluate(
            ExecutionContext(
                call_stack=[script_name],
                stores=data,
                parameters={},
                variables={},
                call_script=call_script,
            )
        )
        data[key] = value

    return data


async def _execute_with_store(
    source: str,
    store_or_store_overrides: Optional[dict[str, Value] | MockStore] = None,
    callable_scripts: Optional[dict[str, CallableScript]] = None,
) -> tuple[Optional[str], MockStore]:
    """Execute a script and return both the output and the store for inspection."""
    lexer: Final = Lexer(source)
    tokens: Final = lexer.tokenize()
    script_name: Final = "!test-script"
    parser: Final = Parser(script_name, tokens)
    script: Final = parser.parse()

    async def _call_script(script_name: str, *args: str) -> str:
        if callable_scripts is None:
            raise ExecutionError(f"There are no callable scripts available to call '{script_name}'")
        if script_name not in callable_scripts:
            raise ExecutionError(f"Called script '{script_name}' not found")
        callee: Final = callable_scripts[script_name]
        return_value: Final = await callee.script.execute(
            persistent_store=callee.store,
            arguments=list(args),
            call_script=_call_script,
        )
        if return_value is None:
            raise ExecutionError(f"Called script '{script_name}' did not return a value")
        return return_value

    match store_or_store_overrides:
        case dict():
            initial_data: Final = await _extract_store_data_from_script(script_name, script, _call_script)
            initial_data.update(
                {StoreKey(script_name, store_name): value for store_name, value in store_or_store_overrides.items()}
            )
            mock_store = MockStore(initial_data)
        case MockStore():
            mock_store = store_or_store_overrides
        case None:
            mock_store = MockStore(await _extract_store_data_from_script(script_name, script, _call_script))
    output = await script.execute(mock_store, [], _call_script)
    return output, mock_store


async def _create_callable_script(script_name: str, source: str) -> CallableScript:
    script: Final = Parser(script_name, Lexer(source).tokenize()).parse()

    async def _call_script(script_name: str, *args: str) -> str:
        raise ExecutionError("No callable scripts available")

    store: Final = MockStore(initial_data=await _extract_store_data_from_script(script_name, script, _call_script))
    return CallableScript(
        script=script,
        store=store,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source", "expected"),
    [
        # Basic execution
        ("PRINT 'Hello, world!';", _Success("Hello, world!")),
        ("STORE counter = 0; counter = counter + 1; PRINT counter;", _Success("1")),
        ("STORE a = 40; PRINT a + 2;", _Success("42")),
        ("PRINT 'Hello' + ', ' + 'world!';", _Success("Hello, world!")),
        ("STORE greeting = 'Hello'; PRINT greeting + ', world!';", _Success("Hello, world!")),
        (r"PRINT 'Line 1\nLine 2';", _Success("Line 1\nLine 2")),
        (r"PRINT 'It\'s working!';", _Success("It's working!")),
        (r"PRINT 'Path: C:\\Users\\John';", _Success(r"Path: C:\Users\John")),
        # Arithmetic
        ("PRINT 10 + 5;", _Success("15")),
        ("PRINT 10 - 3;", _Success("7")),
        ("PRINT 6 * 7;", _Success("42")),
        ("PRINT 20 / 4;", _Success("5")),
        ("PRINT 7 / 2;", _Success("3.5")),
        ("PRINT 10 % 3;", _Success("1")),
        ("PRINT 7 % 2;", _Success("1")),
        ("PRINT 20 % 6;", _Success("2")),
        ("PRINT 15 % 5;", _Success("0")),
        ("PRINT 2 + 3 * 4;", _Success("14")),
        ("PRINT (2 + 3) * 4;", _Success("20")),
        ("PRINT 10 + 5 * 2 - 3 / 3;", _Success("19")),
        ("PRINT 17 % 5 + 3;", _Success("5")),
        ("PRINT 2 * 10 % 3;", _Success("2")),
        ("PRINT 0 % 5;", _Success("0")),
        ("PRINT 5 % 10;", _Success("5")),
        ("PRINT 3.5 % 2;", _Success("1.5")),
        ("PRINT 10 % 0;", _Error(ExecutionError, "Modulo by zero")),
        # Unary
        ("PRINT +42;", _Success("42")),
        ("PRINT -42;", _Success("-42")),
        ("PRINT --5;", _Success("5")),
        ("PRINT 10 + -5;", _Success("5")),
        # String to number - success
        ("PRINT $'42';", _Success("42")),
        ("PRINT $'3.14';", _Success("3.14")),
        ("PRINT $'-17';", _Success("-17")),
        ("PRINT $'0';", _Success("0")),
        ("STORE num_str = '123'; PRINT $num_str;", _Success("123")),
        ("PRINT $('3' + '.14');", _Success("3.14")),
        ("PRINT $'10' + $'20';", _Success("30")),
        ("LET x = '99'; PRINT $x;", _Success("99")),
        # String to number - errors
        (
            "PRINT $'not a number';",
            _Error(ExecutionError, "String 'not a number' does not represent a valid number"),
        ),
        ("PRINT $'';", _Error(ExecutionError, "String '' does not represent a valid number")),
        ("PRINT $'12abc';", _Error(ExecutionError, "String '12abc' does not represent a valid number")),
        # Code evaluation - success
        ("PRINT !'PRINT 5;';", _Success("5")),
        ("PRINT !'PRINT \\'Hello\\';';", _Success("Hello")),
        ("PRINT !'PRINT 2 + 3;';", _Success("5")),
        ("PRINT !'PRINT (10 + 5) * 2;';", _Success("30")),
        ("STORE code = 'PRINT 42;'; PRINT !code;", _Success("42")),
        ("PRINT !('PRINT ' + '99;');", _Success("99")),
        ("LET script = 'PRINT 123;'; PRINT !script;", _Success("123")),
        ("PRINT !'PRINT 1; PRINT 2; PRINT 3;';", _Success("123")),
        ("PRINT !'PRINT \\'Hello\\' + \\' World\\';';", _Success("Hello World")),
        ("PRINT !'PRINT !\\'PRINT 7;\\';';", _Success("7")),
        # Code evaluation - errors
        ("PRINT !'PRINT ;';", _Error(ExecutionError, "Failed to parse code for evaluation")),
        ("PRINT !'STORE x = 5; PRINT x;';", _Error(ExecutionError, "Stores inside evaluated code are not supported")),
        ("PRINT !'PARAMS x; PRINT 5;';", _Error(ExecutionError, "Parameters inside evaluated code are not supported")),
        ("PRINT !'LET x = 5;';", _Error(ExecutionError, "Evaluated script did not produce any output")),
        # Combined conversions
        ("PRINT $!'PRINT \\'42\\';';", _Success("42")),
        ("PRINT !'PRINT $\\'25\\';';", _Success("25")),
        # Store operations
        ("STORE x = 10; x = x * 2; PRINT x;", _Success("20")),
        ("STORE a = 5; STORE b = 3; PRINT a + b;", _Success("8")),
        ("STORE msg = 'Hello'; msg = msg + ' world'; PRINT msg;", _Success("Hello world")),
        ("STORE x = 5 + 3; PRINT x;", _Success("8")),
        ("STORE result = (10 + 5) * 2; PRINT result;", _Success("30")),
        ("STORE a = 10; STORE b = a + 5; PRINT b;", _Success("15")),
        ("STORE x = 3; STORE y = 4; STORE z = x * x + y * y; PRINT z;", _Success("25")),
        ("STORE greeting = 'Hello' + ' World'; PRINT greeting;", _Success("Hello World")),
        ("STORE name = 'Alice'; STORE message = 'Hello, ' + name; PRINT message;", _Success("Hello, Alice")),
        ("STORE a = 1; STORE b = a + 1; STORE c = b + 1; STORE d = c + 1; PRINT d;", _Success("4")),
        # Variable operations
        ("LET x = 42; PRINT x;", _Success("42")),
        ("LET msg = 'Test'; PRINT msg;", _Success("Test")),
        ("LET x = 10; x = 20; PRINT x;", _Success("20")),
        ("LET x = 5; x = x + 10; PRINT x;", _Success("15")),
        ("LET msg = 'Hello'; msg = msg + ' World'; PRINT msg;", _Success("Hello World")),
        ("LET x = 1; x = 2; x = 3; x = 4; PRINT x;", _Success("4")),
        ("LET a = 5; LET b = 3; PRINT a * b;", _Success("15")),
        ("STORE s = 10; LET v = 5; PRINT s + v;", _Success("15")),
        ("STORE s = 5; LET v = 3; v = v + s; PRINT v;", _Success("8")),
        ("LET a = 10; LET b = 20; LET temp = a; a = b; b = temp; PRINT a; PRINT b;", _Success("2010")),
        ("LET sum = 0; sum = sum + 1; sum = sum + 2; sum = sum + 3; PRINT sum;", _Success("6")),
        ("LET result = 'a'; result = result + 'b'; result = result + 'c'; PRINT result;", _Success("abc")),
        ("STORE x = 10; LET y = 5; y = y + x; x = x + y; PRINT x; PRINT y;", _Success("2515")),
        ("LET x = 5; x = 10; x = 15; PRINT x + 5;", _Success("20")),
        # List assignments
        ("LET numbers = [1, 2, 3]; numbers = [4, 5, 6]; PRINT numbers;", _Success("[4, 5, 6]")),
        ("LET numbers = [1, 2, 3]; numbers = []; PRINT numbers;", _Success("[]")),
        ("LET numbers = [1, 2, 3]; numbers = []; PRINT 'type'(numbers);", _Success("list<number>")),
        ("LET words = ['a', 'b']; words = []; PRINT words;", _Success("[]")),
        ("LET flags = [true]; flags = []; PRINT flags;", _Success("[]")),
        ("LET nested = [[1]]; nested = []; PRINT nested;", _Success("[]")),
        ("LET nested: list<list<number>> = []; nested = [[1, 2], [3, 4]]; PRINT nested;", _Success("[[1, 2], [3, 4]]")),
        ("STORE numbers = [1, 2, 3]; numbers = []; PRINT numbers;", _Success("[]")),
        ("LET numbers: list<number> = []; numbers = [1, 2, 3]; numbers = []; PRINT numbers;", _Success("[]")),
        (
            "LET numbers = [1, 2, 3]; numbers = ['string'];",
            _Error(
                AssignmentTypeError,
                "Cannot assign value of type 'list<string>' to target of type 'list<number>'",
            ),
        ),
        (
            "LET n = 10; n = [];",
            _Error(
                EmptyListLiteralAssignmentToNonListError,
                "Cannot assign empty list literal to target of type 'number'.",
            ),
        ),
        # List concatenation
        ("PRINT [1, 2, 3] + [4, 5, 6];", _Success("[1, 2, 3, 4, 5, 6]")),
        ("PRINT ['a', 'b'] + ['c', 'd'];", _Success("[a, b, c, d]")),
        ("PRINT [true] + [false];", _Success("[true, false]")),
        ("PRINT [[1, 2]] + [[3, 4]];", _Success("[[1, 2], [3, 4]]")),
        ("LET a = [1, 2]; LET b = [3, 4]; PRINT a + b;", _Success("[1, 2, 3, 4]")),
        ("LET empty: list<number> = []; PRINT empty + [1, 2, 3];", _Success("[1, 2, 3]")),
        ("LET empty: list<number> = []; PRINT [1, 2, 3] + empty;", _Success("[1, 2, 3]")),
        ("PRINT [1] + [2] + [3];", _Success("[1, 2, 3]")),
        (
            "PRINT [1, 2] + ['string'];",
            _Error(
                ParserTypeError,
                "Operator \\+ is not supported for list operands of different element types",
            ),
        ),
        # Split expressions
        ("PRINT split('hello world');", _Success("[hello, world]")),
        ("PRINT split('a,b,c', ',');", _Success("[a, b, c]")),
        ("PRINT split('one  two  three', '  ');", _Success("[one, two, three]")),
        ("LET text = 'foo-bar-baz'; PRINT split(text, '-');", _Success("[foo, bar, baz]")),
        ("PRINT 'type'(split('test'));", _Success("list<string>")),
        ("PRINT split('single');", _Success("[single]")),
        ("PRINT split('');", _Success("[]")),
        ("LET words = split('alpha beta gamma'); PRINT 'length'(words);", _Success("3")),
        ("LET parts = split('1,2,3,4,5', ','); PRINT parts;", _Success("[1, 2, 3, 4, 5]")),
        # Split expressions with trailing commas
        ("PRINT split('hello world',);", _Success("[hello, world]")),
        ("PRINT split('a,b,c', ',',);", _Success("[a, b, c]")),
        ("LET text = 'x:y:z'; PRINT split(text, ':',);", _Success("[x, y, z]")),
        # Join expressions
        ("PRINT join(['hello', 'world']);", _Success("helloworld")),
        ("PRINT join(['a', 'b', 'c'], ',');", _Success("a,b,c")),
        ("PRINT join(['one', 'two', 'three'], '  ');", _Success("one  two  three")),
        ("LET parts = ['foo', 'bar', 'baz']; PRINT join(parts, '-');", _Success("foo-bar-baz")),
        ("PRINT 'type'(join(['test']));", _Success("string")),
        ("PRINT join(['single']);", _Success("single")),
        ("LET empty: list<string> = []; PRINT join(empty);", _Success("")),
        ("LET words = ['alpha', 'beta', 'gamma']; PRINT 'length'(join(words));", _Success("14")),
        ("LET parts = ['1', '2', '3', '4', '5']; PRINT join(parts, ',');", _Success("1,2,3,4,5")),
        # Join expressions with trailing commas
        ("PRINT join(['hello', 'world'],);", _Success("helloworld")),
        ("PRINT join(['a', 'b', 'c'], ',',);", _Success("a,b,c")),
        ("LET parts = ['x', 'y', 'z']; PRINT join(parts, ':',);", _Success("x:y:z")),
        (
            "PRINT join('not a list');",
            _Error(
                ParserTypeError,
                "join expects a list as the first argument, got 'string'",
            ),
        ),
        (
            "PRINT join([1, 2, 3]);",
            _Error(
                ParserTypeError,
                "join expects a list of strings, got 'list<number>'",
            ),
        ),
        (
            "PRINT join(['text'], 123);",
            _Error(
                ParserTypeError,
                "join expects a string as the second argument, got 'number'",
            ),
        ),
        (
            "PRINT split(123);",
            _Error(
                ParserTypeError,
                "split expects a string as the first argument, got 'number'",
            ),
        ),
        (
            "PRINT split('text', 123);",
            _Error(
                ParserTypeError,
                "split expects a string as the second argument, got 'number'",
            ),
        ),
        # Sort expressions
        (
            "LET words = ['short', 'very long']; LET sorted = sort(words; lhs, rhs yeet "
            + "'length'(lhs) < 'length'(rhs)); PRINT sorted;",
            _Success("[short, very long]"),
        ),
        (
            "LET words = ['short', 'very long']; LET sorted = sort(words; lhs, rhs yeet "
            + "'length'(lhs) > 'length'(rhs)); PRINT sorted;",
            _Success("[very long, short]"),
        ),
        (
            "LET numbers = [3, 1, 4, 1, 5, 9, 2, 6]; LET sorted = sort(numbers; a, b yeet a < b); PRINT sorted;",
            _Success("[1, 1, 2, 3, 4, 5, 6, 9]"),
        ),
        (
            "LET numbers = [3, 1, 4, 1, 5]; LET sorted = sort(numbers; a, b yeet a > b); PRINT sorted;",
            _Success("[5, 4, 3, 1, 1]"),
        ),
        (
            "LET words = ['banana', 'apple', 'cherry']; LET sorted = sort(words; x, y yeet x < y); PRINT sorted;",
            _Success("[apple, banana, cherry]"),
        ),
        ("LET empty: list<number> = []; LET sorted = sort(empty; a, b yeet a < b); PRINT sorted;", _Success("[]")),
        ("LET single = [42]; LET sorted = sort(single; a, b yeet a < b); PRINT sorted;", _Success("[42]")),
        ("PRINT 'type'(sort([1, 2, 3]; a, b yeet a < b));", _Success("list<number>")),
        # Sort expressions without comparison (list<number> only)
        (
            "LET numbers = [3, 1, 4, 1, 5, 9, 2, 6]; LET sorted = sort(numbers); PRINT sorted;",
            _Success("[1, 1, 2, 3, 4, 5, 6, 9]"),
        ),
        ("PRINT sort([5, 2, 8, 1, 9]);", _Success("[1, 2, 5, 8, 9]")),
        ("LET empty: list<number> = []; PRINT sort(empty);", _Success("[]")),
        ("PRINT sort([42]);", _Success("[42]")),
        ("PRINT sort([3.14, 1.41, 2.71]);", _Success("[1.41, 2.71, 3.14]")),
        (
            "PRINT sort(['banana', 'apple']);",
            _Error(
                ParserTypeError,
                "sort without comparison expression is only allowed for list<number>, got 'list<string>'",
            ),
        ),
        (
            "PRINT sort('not a list'; a, b yeet a < b);",
            _Error(
                ParserTypeError,
                "sort expects a list as the first argument, got 'string'",
            ),
        ),
        (
            "PRINT sort([1, 2, 3]; a, b yeet a + b);",
            _Error(
                ParserTypeError,
                "sort comparison expression must return bool, got 'number'",
            ),
        ),
        # Range operators
        ("PRINT 1 ..= 5;", _Success("[1, 2, 3, 4, 5]")),
        ("PRINT 1 ..< 5;", _Success("[1, 2, 3, 4]")),
        ("PRINT 0 ..= 0;", _Success("[0]")),
        ("PRINT 0 ..< 0;", _Success("[]")),
        ("PRINT 5 ..= 1;", _Success("[5, 4, 3, 2, 1]")),
        ("PRINT 5 ..< 1;", _Success("[5, 4, 3, 2]")),
        ("PRINT -2 ..= 2;", _Success("[-2, -1, 0, 1, 2]")),
        ("PRINT -2 ..< 2;", _Success("[-2, -1, 0, 1]")),
        ("LET range = 1 ..= 3; PRINT range;", _Success("[1, 2, 3]")),
        ("PRINT 'type'(1 ..= 5);", _Success("list<number>")),
        ("PRINT 'length'(0 ..= 10);", _Success("11")),
        ("PRINT (1 ..= 5)[2];", _Success("3")),
        ("PRINT for 1 ..= 5 as n yeet n * n;", _Success("[1, 4, 9, 16, 25]")),
        ("PRINT collect 1 ..= 5 as acc, n with acc + n;", _Success("15")),
        (
            "PRINT 1.5 ..= 3;",
            _Error(
                ExecutionError,
                "Range operator ..= requires integer operands, got non-integer start value 1.5",
            ),
        ),
        (
            "PRINT 1 ..= 3.5;",
            _Error(
                ExecutionError,
                "Range operator ..= requires integer operands, got non-integer end value 3.5",
            ),
        ),
        (
            "PRINT 'a' ..= 'z';",
            _Error(
                ParserTypeError,
                "Range operator ..= requires number operands, got 'string' for start",
            ),
        ),
        (
            "PRINT 1.5 ..< 3;",
            _Error(
                ExecutionError,
                "Range operator ..< requires integer operands, got non-integer start value 1.5",
            ),
        ),
        (
            "PRINT 1 ..< 3.5;",
            _Error(
                ExecutionError,
                "Range operator ..< requires integer operands, got non-integer end value 3.5",
            ),
        ),
        # Range operators without spaces
        ("PRINT 1..=5;", _Success("[1, 2, 3, 4, 5]")),
        ("PRINT 1..<5;", _Success("[1, 2, 3, 4]")),
        ("PRINT 10..=1;", _Success("[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]")),
        ("PRINT 0..=0;", _Success("[0]")),
        ("PRINT 0..<0;", _Success("[]")),
        ("PRINT -5..=5;", _Success("[-5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5]")),
        ("LET x = 1..=5; PRINT x;", _Success("[1, 2, 3, 4, 5]")),
        ("PRINT (1..=3)[1];", _Success("2")),
        # Complex sort and calculation test case
        (
            # Advent of Code 2024, Day 1, Part 1 (Example Data)
            "LET input = '3   4\\n4   3\\n2   5\\n1   3\\n3   9\\n3   3'; "
            + r"LET lines = split(input, '\n'); "
            + "LET left = for lines as line yeet $split(line, '   ')[0]; "
            + "LET right = for lines as line yeet $split(line, '   ')[1]; "
            + "LET sorted_left = sort(left); "
            + "LET sorted_right = sort(right); "
            + "LET diffs = for (0 ..< $'length'(sorted_left)) as i yeet $'abs'(sorted_left[i] - sorted_right[i]); "
            + "LET sum = collect diffs as acc, diff with acc + diff; "
            + "PRINT sum;",
            _Success("11"),
        ),
        # Integration
        ("PRINT 'First'; PRINT 'Second'; PRINT 'Third';", _Success("FirstSecondThird")),
        (
            "STORE counter = 0; counter = counter + 1; counter = counter + 1; LET double = counter * 2; PRINT double;",
            _Success("4"),
        ),
        (
            "STORE name = 'Alice'; LET greeting = 'Hello, '; LET message = greeting + name; PRINT message;",
            _Success("Hello, Alice"),
        ),
        ("LET a = 1; LET b = 1; LET c = a + b; LET d = b + c; LET e = c + d; PRINT e;", _Success("5")),
        ("STORE x = 10; LET y = 5; LET z = x * y; PRINT z + 50;", _Success("100")),
        ("PRINT 'a' + 'b' + 'c' + 'd' + 'e';", _Success("abcde")),
        ("STORE first = 'Hello'; STORE last = 'World'; PRINT first + ' ' + last + '!';", _Success("Hello World!")),
        # Edge cases
        ("PRINT 5 - 5;", _Success("0")),
        ("PRINT 3 - 10;", _Success("-7")),
        ("PRINT 3.14 + 2.86;", _Success("6")),
        ("PRINT '';", _Success("")),
        ("PRINT ((2 + 3) * (4 + 1));", _Success("25")),
        # Error handling
        ("PRINT 10 / 0;", _Error(ExecutionError, "Division by zero")),
        ("LET x = 0; PRINT 5 / x;", _Error(ExecutionError, "Division by zero")),
        ("x = 10; PRINT x;", _Error(UnknownVariableError, "Variable 'x' is not defined")),
        ("LET x = 5; PRINT x + undefined;", _Error(UnknownVariableError, "Variable 'undefined' is not defined")),
        (
            "LET x = 5; x = 'string';",
            _Error(AssignmentTypeError, "Cannot assign value of type 'string' to target of type 'number'"),
        ),
        # Boolean operations
        ("PRINT true; PRINT false;", _Success("truefalse")),
        ("PRINT true ? 'Greater' : 'Lesser';", _Success("Greater")),
        ("PRINT false ? 'Greater' : 'Lesser';", _Success("Lesser")),
        ("PRINT true ? 42 : 0;", _Success("42")),
        ("PRINT false ? 42 : 0;", _Success("0")),
        ("PRINT $true; PRINT $false;", _Success("10")),
        ("PRINT true == true; PRINT true == false; PRINT false == false;", _Success("truefalsetrue")),
        ("PRINT 5 == 5; PRINT 5 == 10;", _Success("truefalse")),
        ("PRINT 'test' == 'test'; PRINT 'test' == 'TEST';", _Success("truefalse")),
        ("PRINT true != false; PRINT true != true; PRINT false != false;", _Success("truefalsefalse")),
        ("PRINT 5 != 10; PRINT 5 != 5;", _Success("truefalse")),
        ("PRINT 'test' != 'TEST'; PRINT 'test' != 'test';", _Success("truefalse")),
        # Comparison operators
        ("PRINT 5 < 10; PRINT 10 < 5; PRINT 5 <= 5; PRINT 6 <= 5;", _Success("truefalsetruefalse")),
        ("PRINT 10 > 5; PRINT 5 > 10; PRINT 5 >= 5; PRINT 4 >= 5;", _Success("truefalsetruefalse")),
        ("PRINT 'apple' <= 'banana'; PRINT 'banana' <= 'apple';", _Success("truefalse")),
        ("PRINT 'banana' >= 'apple'; PRINT 'apple' >= 'banana';", _Success("truefalse")),
        ("PRINT 'apple' < 'banana'; PRINT 'banana' < 'apple';", _Success("truefalse")),
        ("PRINT 'banana' > 'apple'; PRINT 'apple' > 'banana';", _Success("truefalse")),
        # Logical operators
        ("PRINT true and true; PRINT true and false; PRINT false and false;", _Success("truefalsefalse")),
        ("PRINT true or false; PRINT false or false; PRINT false or true;", _Success("truefalsetrue")),
        ("PRINT not true; PRINT not false;", _Success("falsetrue")),
        ("PRINT (5 < 10) and (10 < 20); PRINT (5 < 10) and (20 < 10);", _Success("truefalse")),
        ("PRINT (5 > 10) or (10 < 20); PRINT (5 > 10) or (20 < 10);", _Success("truefalse")),
        # To-string conversion
        ("PRINT #42;", _Success("42")),
        ("PRINT #'Hello';", _Success("Hello")),
        ("PRINT #true; PRINT #false;", _Success("truefalse")),
        ("PRINT #(5 + 10);", _Success("15")),
        ("PRINT #1 + #2 + #3;", _Success("123")),
        ("PRINT #3.14;", _Success("3.14")),
        ("PRINT #$'42';", _Success("42")),
        ("PRINT #$!'PRINT 42;';", _Success("42")),
        # To-bool conversion - success
        ("PRINT ?true;", _Success("true")),
        ("PRINT ?false;", _Success("false")),
        ("PRINT ?1;", _Success("true")),
        ("PRINT ?0;", _Success("false")),
        ("PRINT ?3.14;", _Success("true")),
        ("PRINT ?0.0;", _Success("false")),
        ("PRINT ?'true';", _Success("true")),
        ("PRINT ?'false';", _Success("false")),
        # To-bool conversion - error
        ("PRINT ?'hello';", _Error(ExecutionError, "String 'hello' cannot be converted to boolean")),
        # Type errors for non-callable values
        ("PRINT 42();", _Error(TypeNotCallableError, "Value of type 'number' is not callable")),
        ("PRINT true();", _Error(TypeNotCallableError, "Value of type 'bool' is not callable")),
        ("LET x = 10; PRINT x();", _Error(TypeNotCallableError, "Value of type 'number' is not callable")),
        # Subscript operator
        ("PRINT 'Hello'[0];", _Success("H")),
        ("PRINT 'Hello'[4];", _Success("o")),
        ("PRINT 'Hello'[5];", _Error(ExecutionError, "String index 5 out of range")),
        ("PRINT 'Hello'[-1];", _Error(ExecutionError, "String index -1 out of range")),
        ("PRINT 'Hello'[1.5];", _Error(ExecutionError, "String index must be an integer")),
        (
            "PRINT 42[0];",
            _Error(SubscriptOperatorTypeError, "Cannot subscript value of type 'number' with index of type 'number'"),
        ),
        # Builtin type function
        ("PRINT 'type'('Hello');", _Success("string")),
        ("PRINT 'type'(42);", _Success("number")),
        ("PRINT 'type'(true);", _Success("bool")),
        ("PRINT 'type'(1, 2);", _Error(ExecutionError, "Expected 1 argument\\(s\\), got 2")),
        ("PRINT 'type'();", _Error(ExecutionError, "Expected 1 argument\\(s\\), got 0")),
        # String functions - length
        ("PRINT 'length'('hello');", _Success("5")),
        ("PRINT 'length'('');", _Success("0")),
        ("PRINT 'length'(42);", _Error(ExecutionError, "'length' requires a string or list argument, got 'number'")),
        # String functions - upper
        ("PRINT 'upper'('hello');", _Success("HELLO")),
        ("PRINT 'upper'('HeLLo');", _Success("HELLO")),
        ("PRINT 'upper'(42);", _Error(ExecutionError, "'upper' requires a string argument, got 'number'")),
        # String functions - lower
        ("PRINT 'lower'('HELLO');", _Success("hello")),
        ("PRINT 'lower'('HeLLo');", _Success("hello")),
        ("PRINT 'lower'(42);", _Error(ExecutionError, "'lower' requires a string argument, got 'number'")),
        # String functions - trim
        ("PRINT 'trim'('  hello  ');", _Success("hello")),
        ("PRINT 'trim'('hello');", _Success("hello")),
        ("PRINT 'trim'(true);", _Error(ExecutionError, "'trim' requires a string argument, got 'bool'")),
        # String functions - replace
        ("PRINT 'replace'('hello world', 'world', 'there');", _Success("hello there")),
        ("PRINT 'replace'('aaa', 'a', 'b');", _Success("bbb")),
        (
            "PRINT 'replace'(42, 'a', 'b');",
            _Error(ExecutionError, "'replace' can only replace substrings in string arguments, got 'number' instead"),
        ),
        (
            "PRINT 'replace'('hello', 42, 'b');",
            _Error(
                ExecutionError,
                "'replace' requires a string as the second argument for the substring to be replaced, "
                + "got 'number' instead",
            ),
        ),
        (
            "PRINT 'replace'('hello', 'l', 42);",
            _Error(
                ExecutionError,
                "'replace' requires a string as the third argument for the replacement substring, got 'number' instead",
            ),
        ),
        # String functions - contains
        ("PRINT 'contains'('hello world', 'world');", _Success("true")),
        ("PRINT 'contains'('hello world', 'foo');", _Success("false")),
        (
            "PRINT 'contains'(42, 'a');",
            _Error(
                ExecutionError,
                "'contains' requires either both arguments to be strings, or the first argument to be a value "
                + "and the second argument to be a list",
            ),
        ),
        (
            "PRINT 'contains'('hello', true);",
            _Error(
                ExecutionError,
                "'contains' requires either both arguments to be strings, or the first argument to be a value "
                + "and the second argument to be a list",
            ),
        ),
        # String functions - starts_with
        ("PRINT 'starts_with'('hello world', 'hello');", _Success("true")),
        ("PRINT 'starts_with'('hello world', 'world');", _Success("false")),
        (
            "PRINT 'starts_with'(42, 'a');",
            _Error(ExecutionError, "'starts_with' requires string arguments, got 'number' and 'string'"),
        ),
        (
            "PRINT 'starts_with'('hello', 42);",
            _Error(ExecutionError, "'starts_with' requires string arguments, got 'string' and 'number'"),
        ),
        # String functions - ends_with
        ("PRINT 'ends_with'('hello world', 'world');", _Success("true")),
        ("PRINT 'ends_with'('hello world', 'hello');", _Success("false")),
        (
            "PRINT 'ends_with'(42, 'a');",
            _Error(ExecutionError, "'ends_with' requires string arguments, got 'number' and 'string'"),
        ),
        (
            "PRINT 'ends_with'('hello', 42);",
            _Error(ExecutionError, "'ends_with' requires string arguments, got 'string' and 'number'"),
        ),
        # Min/max - success
        ("PRINT 'min'(5);", _Success("5")),
        ("PRINT 'min'(5, 3);", _Success("3")),
        ("PRINT 'min'(5, 3, 8, 1, 9);", _Success("1")),
        ("PRINT 'max'(5);", _Success("5")),
        ("PRINT 'max'(5, 3);", _Success("5")),
        ("PRINT 'max'(5, 3, 8, 1, 9);", _Success("9")),
        # Min/max - errors
        ("PRINT 'min'();", _Error(ExecutionError, "Expected at least 1 argument\\(s\\), got 0")),
        ("PRINT 'max'();", _Error(ExecutionError, "Expected at least 1 argument\\(s\\), got 0")),
        (
            "PRINT 'min'('hello', 3);",
            _Error(ExecutionError, "'min' requires number arguments, got string at position 1"),
        ),
        ("PRINT 'min'(5, true);", _Error(ExecutionError, "'min' requires number arguments, got bool at position 2")),
        (
            "PRINT 'min'(1, 2, 'three');",
            _Error(ExecutionError, "'min' requires number arguments, got string at position 3"),
        ),
        (
            "PRINT 'max'('hello', 3);",
            _Error(ExecutionError, "'max' requires number arguments, got string at position 1"),
        ),
        ("PRINT 'max'(5, false);", _Error(ExecutionError, "'max' requires number arguments, got bool at position 2")),
        (
            "PRINT 'max'(1, 2, 'three');",
            _Error(ExecutionError, "'max' requires number arguments, got string at position 3"),
        ),
        # Math functions - abs
        ("PRINT 'abs'(5);", _Success("5")),
        ("PRINT 'abs'(-5);", _Success("5")),
        ("PRINT 'abs'(0);", _Success("0")),
        ("PRINT 'abs'(-3.14);", _Success("3.14")),
        ("PRINT 'abs'('hello');", _Error(ExecutionError, "'abs' requires a number argument, got string")),
        # Math functions - round
        ("PRINT 'round'(3.4);", _Success("3")),
        ("PRINT 'round'(3.6);", _Success("4")),
        ("PRINT 'round'(3.5);", _Success("4")),
        ("PRINT 'round'(-3.6);", _Success("-4")),
        ("PRINT 'round'('hello');", _Error(ExecutionError, "'round' requires a number argument, got string")),
        # Math functions - floor
        ("PRINT 'floor'(3.9);", _Success("3")),
        ("PRINT 'floor'(5);", _Success("5")),
        ("PRINT 'floor'(-3.1);", _Success("-4")),
        ("PRINT 'floor'(true);", _Error(ExecutionError, "'floor' requires a number argument, got bool")),
        # Math functions - ceil
        ("PRINT 'ceil'(3.1);", _Success("4")),
        ("PRINT 'ceil'(5);", _Success("5")),
        ("PRINT 'ceil'(-3.9);", _Success("-3")),
        ("PRINT 'ceil'('test');", _Error(ExecutionError, "'ceil' requires a number argument, got string")),
        # Math functions - sqrt
        ("PRINT 'sqrt'(16);", _Success("4")),
        ("PRINT 'sqrt'(0);", _Success("0")),
        ("PRINT 'sqrt'('hello');", _Error(ExecutionError, "'sqrt' requires a number argument, got string")),
        ("PRINT 'sqrt'(-4);", _Error(ExecutionError, "'sqrt' requires a non-negative argument, got -4")),
        # Math functions - pow
        ("PRINT 'pow'(2, 3);", _Success("8")),
        ("PRINT 'pow'(5, 0);", _Success("1")),
        ("PRINT 'pow'(2, -1);", _Success("0.5")),
        ("PRINT 'pow'(4, 0.5);", _Success("2")),
        (
            "PRINT 'pow'('hello', 2);",
            _Error(ExecutionError, "'pow' requires number arguments, got string at position 1"),
        ),
        ("PRINT 'pow'(2, true);", _Error(ExecutionError, "'pow' requires number arguments, got bool at position 2")),
        # Math functions - random (range validation)
        (
            "PRINT 'random'('hello', 10);",
            _Error(ExecutionError, "'random' requires number arguments, got string at position 1"),
        ),
        (
            "PRINT 'random'(1, false);",
            _Error(ExecutionError, "'random' requires number arguments, got bool at position 2"),
        ),
        # Date function
        ("PRINT 'date'(42);", _Error(ExecutionError, "'date' requires a string argument, got number")),
        # Explicit type hints
        ("LET x: number = 10; PRINT x;", _Success("10")),
        ("LET msg: string = 'Hello'; PRINT msg;", _Success("Hello")),
        ("LET flag: bool = true; PRINT flag;", _Success("true")),
        (
            "LET x: number = 'not a number';",
            _Error(
                InitializationTypeError, "Cannot initialize variable 'x' of type 'number' with value of type 'string'"
            ),
        ),
        (
            "LET msg: string = 42;",
            _Error(
                InitializationTypeError, "Cannot initialize variable 'msg' of type 'string' with value of type 'number'"
            ),
        ),
        (
            "LET flag: bool = 'not a bool';",
            _Error(
                InitializationTypeError, "Cannot initialize variable 'flag' of type 'bool' with value of type 'string'"
            ),
        ),
        # Lists
        ("LET empty_list: list<string> = []; PRINT 'type'(empty_list);", _Success("list<string>")),
        ("LET empty_list: list<number> = []; PRINT 'type'(empty_list);", _Success("list<number>")),
        ("LET empty_list: list<bool> = []; PRINT 'type'(empty_list);", _Success("list<bool>")),
        ("LET empty_list: list<list<string>> = []; PRINT 'type'(empty_list);", _Success("list<list<string>>")),
        (
            "LET empty_list = [];",
            _Error(
                EmptyListLiteralWithoutTypeAnnotationError,
                "Empty list literal requires an explicit type annotation.",
            ),
        ),
        ("LET words: list<string> = ['Hello, ', 'world!']; PRINT 'type'(words);", _Success("list<string>")),
        (
            "LET words: list<number> = ['Hello, ', 'world!'];",
            _Error(
                InitializationTypeError,
                "Cannot initialize variable 'words' of type 'list<number>' with value of type 'list<string>'.",
            ),
        ),
        (
            "LET elements = [42, 'not a number'];",
            _Error(ListElementTypeMismatchError, "List element type mismatch: expected 'number', got 'string'."),
        ),
        ("LET elements: list<list<number>> = [[], [1, 2, 3]]; PRINT 'type'(elements);", _Success("list<list<number>>")),
        ("LET elements = [[], [1, 2, 3]]; PRINT 'type'(elements);", _Success("list<list<number>>")),
        ("LET elements = [[1], [], [], [], [2, 3, 4]]; PRINT 'type'(elements);", _Success("list<list<number>>")),
        (
            "LET elements = [[], [], []];",
            _Error(
                EmptyListLiteralWithoutTypeAnnotationError, "Empty list literal requires an explicit type annotation."
            ),
        ),
        ("LET elements: list<list<number>> = [[], [], []]; PRINT 'type'(elements);", _Success("list<list<number>>")),
        (
            "LET elements: list<list<number>> = [[], [[]]]; PRINT 'type'(elements);",
            _Error(
                ExpectedEmptyListLiteralError,
                r"Expected an empty list literal, got a list literal with 1 element\(s\).",
            ),
        ),
        ("LET words = ['Hello, ', 'world!']; PRINT words;", _Success("[Hello, , world!]")),
        ("LET numbers = [1, 2, 3, 4]; PRINT numbers;", _Success("[1, 2, 3, 4]")),
        ("LET flags = [true, false, true]; PRINT flags;", _Success("[true, false, true]")),
        ("LET nested = [[1, 2], [3, 4]]; PRINT nested;", _Success("[[1, 2], [3, 4]]")),
        ("PRINT [1, 2, 3];", _Success("[1, 2, 3]")),
        ("PRINT [1, 2, 3][0];", _Success("1")),
        ("PRINT [1, 2, 3][3];", _Error(ExecutionError, "List index 3 out of range for list of length 3")),
        ("PRINT [1, 2, 3][2.5];", _Error(ExecutionError, "List index must be an integer, got non-integer 2.5")),
        ("PRINT [1, 2, 3][-1];", _Error(ExecutionError, "List index -1 out of range for list of length 3")),
        ("PRINT [][0];", _Error(ExecutionError, "Unable to deduce type of empty list literal.")),
        ("PRINT [[1, 2, 3], [4, 5], [6, 7]][1][0];", _Success("4")),
        ("STORE my_list = [10, 20, 30]; PRINT my_list[1];", _Success("20")),
        ("PRINT 'length'([1, 2, 3, 4, 5]);", _Success("5")),
        ("LET numbers: list<number> = []; PRINT 'length'(numbers);", _Success("0")),
        ("PRINT 'contains'([1, 2, 3, 4], 3);", _Success("true")),
        ("PRINT 'contains'([1, 2, 3, 4], 5);", _Success("false")),
        (
            "PRINT 'contains'([1, 2, 3, 4], '3');",
            _Error(
                ExecutionError,
                "'contains' requires the needle to be of the same type as the elements of the haystack list, "
                + "got 'string' and 'list<number>'",
            ),
        ),
        ("PRINT 'min'([5, 3, 8, 1, 9]);", _Success("1")),
        (
            "PRINT 'min'(['should', 'fail']);",
            _Error(ExecutionError, "'min' requires number arguments, got list of string"),
        ),
        ("PRINT 'max'([5, 3, 8, 1, 9]);", _Success("9")),
        (
            "PRINT 'max'(['should', 'fail']);",
            _Error(ExecutionError, "'max' requires number arguments, got list of string"),
        ),
        # List comprehensions
        (
            "LET words = ['123', '456']; PRINT 'type'(for words as word yeet $word);",
            _Success("list<number>"),
        ),
        (
            "LET words = ['123', '456']; LET numbers = for words as word yeet $word; PRINT numbers;",
            _Success("[123, 456]"),
        ),
        (
            "LET shadowed = 0; LET words = ['123', '456']; LET numbers = for words as shadowed yeet $shadowed;",
            _Error(VariableRedefinitionError, "Variable 'shadowed' is already defined."),
        ),
        (
            "STORE shadowed = 0; LET words = ['123', '456']; LET numbers = for words as shadowed yeet $shadowed;",
            _Error(VariableShadowsStoreError, "Variable 'shadowed' shadows store with the same name."),
        ),
        (
            "PARAMS shadowed; LET words = ['123', '456']; LET numbers = for words as shadowed yeet $shadowed;",
            _Error(VariableShadowsParameterError, "Variable 'shadowed' shadows parameter with the same name."),
        ),
        (
            "LET words = ['123', '456']; LET numbers = for words as word yeet $unknown;",
            _Error(UnknownVariableError, "Variable 'unknown' is not defined."),
        ),
        (
            "LET numbers = for words as word yeet $word;",
            _Error(UnknownVariableError, "Variable 'words' is not defined."),
        ),
        (
            "PRINT for [1, 2, 3, 4, 5] as num yeet num * num;",
            _Success("[1, 4, 9, 16, 25]"),
        ),
        (
            "PRINT for [] as item yeet 'should fail';",
            _Error(ExecutionError, "Unable to deduce type of empty list literal."),
        ),
        (
            "LET nested_lists = [[1, 2], [3, 4], [5]]; "
            + "PRINT for nested_lists as sublist yeet for sublist as num yeet num * 2;",
            _Error(
                NestedListComprehensionsWithoutParenthesesError,
                "Nested list comprehensions must be enclosed in parentheses.",
            ),
        ),
        (
            "LET nested_lists = [[1, 2], [3, 4], [5]]; "
            + "PRINT (for nested_lists as sublist yeet (for sublist as num yeet num * 2));",
            _Success("[[2, 4], [6, 8], [10]]"),
        ),
        (
            "LET words = ['apple', 'banana', 'cherry']; " + "PRINT for words as word yeet 'upper'(word);",
            _Success("[APPLE, BANANA, CHERRY]"),
        ),
        (
            "LET numbers = [1, 2, 3, 4, 5]; PRINT for numbers as num if num > 3 yeet num;",
            _Success("[4, 5]"),
        ),
        (
            "LET words = ['apple', 'acorn', 'banana', 'avocado'];"
            + "PRINT for words as word if ?'starts_with'(word, 'a') yeet word;",
            _Success("[apple, acorn, avocado]"),
        ),
        # Collect
        (
            "LET numbers = [1, 2, 3];"
            + "LET sum = collect numbers as accumulator, element with accumulator + element;"
            + "PRINT sum;",
            _Success("6"),
        ),
        (
            "LET numbers = [1, 2, 3];"
            + "LET product = collect numbers as acc, elem with acc * elem;"
            + "PRINT product;",
            _Success("6"),
        ),
        (
            "LET words = ['Hello', ' ', 'World', '!'];"
            + "LET message = collect words as acc, elem with acc + elem;"
            + "PRINT message;",
            _Success("Hello World!"),
        ),
        (
            "LET result = collect [] as acc, elem with acc + elem;" + "PRINT result;",
            _Error(
                ExecutionError,
                "Unable to deduce type of empty list literal.",
            ),
        ),
        (
            "LET shadowed = 0; LET result = collect [1, 2, 3] as shadowed, elem with shadowed + elem;"
            + "PRINT result;",
            _Error(
                VariableRedefinitionError,
                "Variable 'shadowed' is already defined",
            ),
        ),
        (
            "LET shadowed = 0; LET result = collect [1, 2, 3] as acc, shadowed with acc + shadowed;" + "PRINT result;",
            _Error(
                VariableRedefinitionError,
                "Variable 'shadowed' is already defined",
            ),
        ),
        (
            "STORE shadowed = 0; LET result = collect [1, 2, 3] as shadowed, elem with shadowed + elem;"
            + "PRINT result;",
            _Error(
                VariableShadowsStoreError,
                "Variable 'shadowed' shadows store with the same name.",
            ),
        ),
        (
            "STORE shadowed = 0; LET result = collect [1, 2, 3] as acc, shadowed with acc + shadowed;"
            + "PRINT result;",
            _Error(
                VariableShadowsStoreError,
                "Variable 'shadowed' shadows store with the same name.",
            ),
        ),
        (
            "PARAMS shadowed; LET result = collect [1, 2, 3] as shadowed, elem with shadowed + elem;" + "PRINT result;",
            _Error(
                VariableShadowsParameterError,
                "Variable 'shadowed' shadows parameter with the same name.",
            ),
        ),
        (
            "PARAMS shadowed; LET result = collect [1, 2, 3] as acc, shadowed with acc + shadowed;" + "PRINT result;",
            _Error(
                VariableShadowsParameterError,
                "Variable 'shadowed' shadows parameter with the same name.",
            ),
        ),
        (
            "LET words = ['Hello', ' ', 'World', '!'];" + "LET message = collect words as acc, elem with $acc + $elem;",
            _Error(
                CollectExpressionTypeError,
                "Collect expression type error: expected 'string', got 'number'.",
            ),
        ),
        (
            """LET nested = [[1, 2], [3, 4], [5]];
LET sum = collect (
    for nested as inner_list yeet (
        collect inner_list as acc, num with acc + num
    )
) as outer_acc, inner_sum with outer_acc + inner_sum;
PRINT sum;""",
            _Success("15"),
        ),
    ],
)
async def test_script_execution(source: str, expected: _Result) -> None:
    match expected:
        case _Success(output):
            result = await _execute(source)
            assert result == output
        case _Error(error_type, error_match):
            with pytest.raises(error_type, match=error_match):
                await _execute(source)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source", "expected_output", "store_name", "expected_value"),
    [
        ("STORE counter = 10; LET x = counter; x = 20; PRINT counter;", "10", "counter", NumberValue(value=10.0)),
        ("STORE counter = 10; counter = 20; PRINT counter;", "20", "counter", NumberValue(value=20.0)),
        ("STORE value = 5; value = value * 3 + 2; PRINT value;", "17", "value", NumberValue(value=17.0)),
        ("STORE x = 1; x = x + 1; x = x + 1; x = x + 1; PRINT x;", "4", "x", NumberValue(value=4.0)),
        (
            "STORE msg = 'Hello'; msg = msg + ' World'; PRINT msg;",
            "Hello World",
            "msg",
            StringValue(value="Hello World"),
        ),
        ("STORE a = 10; LET b = a; a = 20; b = 30; PRINT a; PRINT b;", "2030", "a", NumberValue(value=20.0)),
    ],
)
async def test_store_state_validation(
    source: str, expected_output: str, store_name: str, expected_value: Value
) -> None:
    output, store = await _execute_with_store(source)
    assert output == expected_output
    key = StoreKey("!test-script", store_name)
    assert store.get_value(key) == expected_value


@pytest.mark.asyncio
async def test_sqrt_with_approximation() -> None:
    output = await _execute("PRINT 'sqrt'(2);")
    assert output is not None
    assert float(output) == pytest.approx(1.4142135623730951)  # type: ignore[reportUnknownMemberType]


@pytest.mark.asyncio
async def test_random_in_range() -> None:
    output = await _execute("PRINT 'random'(1, 10);")
    assert output is not None
    value = float(output)
    assert 1 <= value <= 10

    output = await _execute("PRINT 'random'(5, 5);")
    assert output is not None
    assert float(output) == pytest.approx(5)  # type: ignore[reportUnknownMemberType]

    output = await _execute("PRINT 'random'(-10, -5);")
    assert output is not None
    value = float(output)
    assert -10 <= value <= -5


@pytest.mark.asyncio
async def test_timestamp_function() -> None:
    output = await _execute("PRINT 'timestamp'();")
    assert output is not None
    value = float(output)
    assert value > 1577836800  # 2020-01-01 00:00:00 UTC


@pytest.mark.asyncio
async def test_date_function() -> None:
    output = await _execute("PRINT 'date'('%Y');")
    assert output is not None
    assert len(output) == 4
    assert output.isdigit()
    assert int(output) >= 2025

    output = await _execute("PRINT 'date'('%Y-%m-%d');")
    assert output is not None
    assert re.match(r"\d{4}-\d{2}-\d{2}", output)


@pytest.mark.asyncio
async def test_call_operator() -> None:
    other_script = await _create_callable_script("other", "PRINT 'Hello from other script!';")
    output = await _execute("PRINT 'other'();", callable_scripts={"other": other_script})
    assert output == "Hello from other script!"

    addition_script = await _create_callable_script("add", "PARAMS a, b; PRINT $a + $b;")
    output = await _execute("PRINT 'add'( '10', '32' );", callable_scripts={"add": addition_script})
    assert output == "42"

    fibonacci_script = await _create_callable_script(
        "fibonacci", "STORE a = 0; STORE b = 1; LET temp = a; a = b; b = temp + b; PRINT b;"
    )
    output = await _execute(
        "PRINT 'fibonacci'() + ', ' + 'fibonacci'() + ', ' + 'fibonacci'() + ', ' + 'fibonacci'();",
        callable_scripts={"fibonacci": fibonacci_script},
    )
    assert output == "1, 2, 3, 5"


@pytest.mark.asyncio
async def test_recursion() -> None:
    source: Final = (
        "PARAMS input; LET n = $input; PRINT n <= 1 ? '1' : #($('fibonacci'(n - 1)) + $('fibonacci'(n - 2)));"
    )
    lexer: Final = Lexer(source)
    tokens: Final = lexer.tokenize()
    parser: Final = Parser("fibonacci", tokens)
    script: Final = parser.parse()

    async def _script_caller(script_name: str, *args: str) -> str:
        if script_name != "fibonacci":
            raise ExecutionError(f"Called script '{script_name}' not found")
        return_value: Final = await script.execute(
            persistent_store=MockStore(initial_data={}), arguments=list(args), call_script=_script_caller
        )
        if return_value is None:
            raise ExecutionError(f"Called script '{script_name}' did not return a value")
        return return_value

    output: Final = await _script_caller("fibonacci", "8")
    assert output == "34"


def test_builtin_function_arity() -> None:
    type_function: Final = BUILTIN_FUNCTIONS["type"]
    assert type_function.arity == 1
    min_function: Final = BUILTIN_FUNCTIONS["min"]
    assert min_function.arity == _Variadic.with_min_num_arguments(1)
    max_function: Final = BUILTIN_FUNCTIONS["max"]
    assert max_function.arity == _Variadic.with_min_num_arguments(1)
