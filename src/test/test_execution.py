from typing import Final
from typing import Optional

import pytest

from chatbot2k.scripting_engine.lexer import Lexer
from chatbot2k.scripting_engine.parser import Parser
from chatbot2k.scripting_engine.parser import UnknownVariableError
from chatbot2k.scripting_engine.stores import StoreKey
from chatbot2k.scripting_engine.types.execution_error import ExecutionError
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


# String operations
def test_string_concatenation() -> None:
    output: Final = _execute("PRINT 'Hello' + ', ' + 'world!';")
    assert output == "Hello, world!"


def test_string_concatenation_with_store() -> None:
    output: Final = _execute("STORE greeting = 'Hello'; PRINT greeting + ', world!';")
    assert output == "Hello, world!"


def test_string_with_escape_sequences() -> None:
    output: Final = _execute(r"PRINT 'Line 1\nLine 2';")
    assert output == "Line 1\nLine 2"


def test_string_with_escaped_quote() -> None:
    output: Final = _execute(r"PRINT 'It\'s working!';")
    assert output == "It's working!"


# Number operations
def test_addition() -> None:
    output: Final = _execute("PRINT 10 + 5;")
    assert output == "15"


def test_subtraction() -> None:
    output: Final = _execute("PRINT 10 - 3;")
    assert output == "7"


def test_multiplication() -> None:
    output: Final = _execute("PRINT 6 * 7;")
    assert output == "42"


def test_division() -> None:
    output: Final = _execute("PRINT 20 / 4;")
    assert output == "5"


def test_float_division() -> None:
    output: Final = _execute("PRINT 7 / 2;")
    assert output == "3.5"


def test_operator_precedence() -> None:
    output: Final = _execute("PRINT 2 + 3 * 4;")
    assert output == "14"


def test_operator_precedence_with_parentheses() -> None:
    output: Final = _execute("PRINT (2 + 3) * 4;")
    assert output == "20"


def test_complex_arithmetic() -> None:
    output: Final = _execute("PRINT 10 + 5 * 2 - 3 / 3;")
    assert output == "19"


# Unary operations
def test_unary_plus() -> None:
    output: Final = _execute("PRINT +42;")
    assert output == "42"


def test_unary_minus() -> None:
    output: Final = _execute("PRINT -42;")
    assert output == "-42"


def test_double_negation() -> None:
    output: Final = _execute("PRINT --5;")
    assert output == "5"


def test_unary_in_expression() -> None:
    output: Final = _execute("PRINT 10 + -5;")
    assert output == "5"


# Store operations
def test_store_update() -> None:
    output: Final = _execute("STORE x = 10; x = x * 2; PRINT x;")
    assert output == "20"


def test_multiple_stores() -> None:
    output: Final = _execute("STORE a = 5; STORE b = 3; PRINT a + b;")
    assert output == "8"


def test_store_string_update() -> None:
    output: Final = _execute("STORE msg = 'Hello'; msg = msg + ' world'; PRINT msg;")
    assert output == "Hello world"


# Variable operations
def test_variable_definition() -> None:
    output: Final = _execute("LET x = 42; PRINT x;")
    assert output == "42"


def test_variable_string_definition() -> None:
    output: Final = _execute("LET msg = 'Test'; PRINT msg;")
    assert output == "Test"


def test_variable_reassignment() -> None:
    output: Final = _execute("LET x = 10; x = 20; PRINT x;")
    assert output == "20"


def test_variable_reassignment_with_expression() -> None:
    output: Final = _execute("LET x = 5; x = x + 10; PRINT x;")
    assert output == "15"


def test_variable_reassignment_string() -> None:
    output: Final = _execute("LET msg = 'Hello'; msg = msg + ' World'; PRINT msg;")
    assert output == "Hello World"


def test_variable_multiple_reassignments() -> None:
    output: Final = _execute("LET x = 1; x = 2; x = 3; x = 4; PRINT x;")
    assert output == "4"


def test_variable_in_expression() -> None:
    output: Final = _execute("LET a = 5; LET b = 3; PRINT a * b;")
    assert output == "15"


def test_variable_and_store_interaction() -> None:
    output: Final = _execute("STORE s = 10; LET v = 5; PRINT s + v;")
    assert output == "15"


# Multiple statements
def test_multiple_print_statements() -> None:
    # All print outputs are concatenated
    output: Final = _execute("PRINT 'First'; PRINT 'Second'; PRINT 'Third';")
    assert output == "FirstSecondThird"


def test_complex_script() -> None:
    output: Final = _execute(
        "STORE counter = 0; counter = counter + 1; counter = counter + 1; LET double = counter * 2; PRINT double;"
    )
    assert output == "4"


def test_string_building() -> None:
    output: Final = _execute(
        "STORE name = 'Alice'; LET greeting = 'Hello, '; LET message = greeting + name; PRINT message;"
    )
    assert output == "Hello, Alice"


# Edge cases
def test_zero_result() -> None:
    output: Final = _execute("PRINT 5 - 5;")
    assert output == "0"


def test_negative_result() -> None:
    output: Final = _execute("PRINT 3 - 10;")
    assert output == "-7"


def test_decimal_numbers() -> None:
    output: Final = _execute("PRINT 3.14 + 2.86;")
    assert output == "6"


def test_empty_string() -> None:
    output: Final = _execute("PRINT '';")
    assert output == ""


def test_nested_parentheses() -> None:
    output: Final = _execute("PRINT ((2 + 3) * (4 + 1));")
    assert output == "25"


# Error handling tests
def test_division_by_zero() -> None:
    with pytest.raises(ExecutionError, match="Division by zero"):
        _execute("PRINT 10 / 0;")


def test_division_by_zero_in_variable() -> None:
    with pytest.raises(ExecutionError, match="Division by zero"):
        _execute("LET x = 0; PRINT 5 / x;")


# Integration tests
def test_fibonacci_calculation() -> None:
    output: Final = _execute("LET a = 1; LET b = 1; LET c = a + b; LET d = b + c; LET e = c + d; PRINT e;")
    assert output == "5"


def test_multiple_operations_with_stores_and_variables() -> None:
    output: Final = _execute("STORE x = 10; LET y = 5; LET z = x * y; PRINT z + 50;")
    assert output == "100"


def test_concatenate_multiple_strings() -> None:
    output: Final = _execute("PRINT 'a' + 'b' + 'c' + 'd' + 'e';")
    assert output == "abcde"


def test_store_string_concatenation_complex() -> None:
    output: Final = _execute("STORE first = 'Hello'; STORE last = 'World'; PRINT first + ' ' + last + '!';")
    assert output == "Hello World!"


# Variable reassignment and complex scenarios
def test_variable_with_store_in_expression() -> None:
    output: Final = _execute("STORE s = 5; LET v = 3; v = v + s; PRINT v;")
    assert output == "8"


def test_swap_like_pattern() -> None:
    output: Final = _execute("LET a = 10; LET b = 20; LET temp = a; a = b; b = temp; PRINT a; PRINT b;")
    assert output == "2010"


def test_variable_reassignment_in_loop_like_pattern() -> None:
    output: Final = _execute("LET sum = 0; sum = sum + 1; sum = sum + 2; sum = sum + 3; PRINT sum;")
    assert output == "6"


def test_variable_string_building() -> None:
    output: Final = _execute("LET result = 'a'; result = result + 'b'; result = result + 'c'; PRINT result;")
    assert output == "abc"


def test_mixed_stores_and_variables() -> None:
    output: Final = _execute("STORE x = 10; LET y = 5; y = y + x; x = x + y; PRINT x; PRINT y;")
    assert output == "2515"


# Error cases for variables
def test_reassign_undefined_variable_raises() -> None:
    with pytest.raises(UnknownVariableError, match="Variable 'x' is not defined"):
        _execute("x = 10; PRINT x;")


def test_use_undefined_variable_in_expression_raises() -> None:
    with pytest.raises(UnknownVariableError, match="Variable 'undefined' is not defined"):
        _execute("LET x = 5; PRINT x + undefined;")


def test_variable_type_consistency() -> None:
    # Variables maintain their type through reassignment
    output: Final = _execute("LET x = 5; x = 10; x = 15; PRINT x + 5;")
    assert output == "20"


def test_variable_type_change_raises() -> None:
    with pytest.raises(
        ExecutionError,
        match="Type mismatch when assigning to variable 'x': expected number, got string",
    ):
        _execute("LET x = 5; x = 'string';")
