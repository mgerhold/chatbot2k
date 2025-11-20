from chatbot2k.scripting_engine.parser import AssignmentTypeError
from typing import Final
from typing import Optional

import pytest

from chatbot2k.scripting_engine.lexer import Lexer
from chatbot2k.scripting_engine.parser import Parser
from chatbot2k.scripting_engine.parser import UnknownVariableError
from chatbot2k.scripting_engine.stores import StoreKey
from chatbot2k.scripting_engine.types.execution_error import ExecutionError
from chatbot2k.scripting_engine.types.value import NumberValue
from chatbot2k.scripting_engine.types.value import StringValue
from chatbot2k.scripting_engine.types.value import Value
from test.mock_store import MockStore


def _execute(source: str, store_overrides: Optional[dict[str, Value]] = None) -> Optional[str]:
    output, _ = _execute_with_store(source, store_overrides)
    return output


def _execute_with_store(
    source: str,
    store_overrides: Optional[dict[str, Value]] = None,
) -> tuple[Optional[str], MockStore]:
    """Execute a script and return both the output and the store for inspection."""
    lexer: Final = Lexer(source)
    tokens: Final = lexer.tokenize()
    script_name: Final = "!test-script"
    parser: Final = Parser(script_name, tokens)
    script: Final = parser.parse()

    initial_data: Final[dict[StoreKey, Value]] = {}
    for store in script.stores:
        key = StoreKey(script_name, store.name)
        value = store.value.evaluate(script_name, initial_data, {}, {})
        initial_data[key] = value

    if store_overrides is not None:
        initial_data.update({StoreKey(script_name, store_name): value for store_name, value in store_overrides.items()})

    mock_store = MockStore(initial_data)
    output = script.execute(mock_store, [])
    return output, mock_store


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


def test_string_with_escaped_backslash() -> None:
    output: Final = _execute(r"PRINT 'Path: C:\\Users\\John';")
    assert output == r"Path: C:\Users\John"


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


# String to number conversion tests
def test_string_to_number_with_integer_string() -> None:
    output: Final = _execute("PRINT $'42';")
    assert output == "42"


def test_string_to_number_with_float_string() -> None:
    output: Final = _execute("PRINT $'3.14';")
    assert output == "3.14"


def test_string_to_number_with_negative_string() -> None:
    output: Final = _execute("PRINT $'-17';")
    assert output == "-17"


def test_string_to_number_with_zero_string() -> None:
    output: Final = _execute("PRINT $'0';")
    assert output == "0"


def test_string_to_number_with_store() -> None:
    output: Final = _execute("STORE num_str = '123'; PRINT $num_str;")
    assert output == "123"


def test_string_to_number_with_concatenated_strings() -> None:
    output: Final = _execute("PRINT $('3' + '.14');")
    assert output == "3.14"


def test_string_to_number_in_arithmetic_expression() -> None:
    output: Final = _execute("PRINT $'10' + $'20';")
    assert output == "30"


def test_string_to_number_with_variable() -> None:
    output: Final = _execute("LET x = '99'; PRINT $x;")
    assert output == "99"


def test_string_to_number_with_invalid_string_raises_error() -> None:
    with pytest.raises(ExecutionError, match="String 'not a number' does not represent a valid number"):
        _execute("PRINT $'not a number';")


def test_string_to_number_with_empty_string_raises_error() -> None:
    with pytest.raises(ExecutionError, match="String '' does not represent a valid number"):
        _execute("PRINT $'';")


def test_string_to_number_with_partial_number_raises_error() -> None:
    with pytest.raises(ExecutionError, match="String '12abc' does not represent a valid number"):
        _execute("PRINT $'12abc';")


# Evaluate string as code tests
def test_evaluate_simple_expression() -> None:
    output: Final = _execute("PRINT !'PRINT 5;';")
    assert output == "5"


def test_evaluate_string_literal() -> None:
    output: Final = _execute("PRINT !'PRINT \\'Hello\\';';")
    assert output == "Hello"


def test_evaluate_arithmetic_expression() -> None:
    output: Final = _execute("PRINT !'PRINT 2 + 3;';")
    assert output == "5"


def test_evaluate_complex_expression() -> None:
    output: Final = _execute("PRINT !'PRINT (10 + 5) * 2;';")
    assert output == "30"


def test_evaluate_with_store() -> None:
    output: Final = _execute("STORE code = 'PRINT 42;'; PRINT !code;")
    assert output == "42"


def test_evaluate_with_concatenated_code() -> None:
    output: Final = _execute("PRINT !('PRINT ' + '99;');")
    assert output == "99"


def test_evaluate_with_variable() -> None:
    output: Final = _execute("LET script = 'PRINT 123;'; PRINT !script;")
    assert output == "123"


def test_evaluate_multiple_statements() -> None:
    output: Final = _execute("PRINT !'PRINT 1; PRINT 2; PRINT 3;';")
    assert output == "123"


def test_evaluate_with_string_concatenation_in_code() -> None:
    output: Final = _execute("PRINT !'PRINT \\'Hello\\' + \\' World\\';';")
    assert output == "Hello World"


def test_evaluate_invalid_syntax_raises_error() -> None:
    with pytest.raises(ExecutionError, match="Failed to parse code for evaluation"):
        _execute("PRINT !'PRINT ;';")


def test_evaluate_code_with_stores_raises_error() -> None:
    with pytest.raises(ExecutionError, match="Stores inside evaluated code are not supported"):
        _execute("PRINT !'STORE x = 5; PRINT x;';")


def test_evaluate_code_with_parameters_raises_error() -> None:
    with pytest.raises(ExecutionError, match="Parameters inside evaluated code are not supported"):
        _execute("PRINT !'PARAMS x; PRINT 5;';")


def test_evaluate_code_without_output_raises_error() -> None:
    with pytest.raises(ExecutionError, match="Evaluated script did not produce any output"):
        _execute("PRINT !'LET x = 5;';")


def test_evaluate_nested_evaluation() -> None:
    # Test evaluating code that itself contains evaluation
    output: Final = _execute("PRINT !'PRINT !\\'PRINT 7;\\';';")
    assert output == "7"


# Combined tests for string to number and evaluate
def test_string_to_number_and_evaluate_combined() -> None:
    output: Final = _execute("PRINT $!'PRINT \\'42\\';';")
    assert output == "42"


def test_evaluate_expression_with_string_to_number() -> None:
    output: Final = _execute("PRINT !'PRINT $\\'25\\';';")
    assert output == "25"


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


def test_store_with_expression() -> None:
    """Test that store definitions can use expressions."""
    output: Final = _execute("STORE x = 5 + 3; PRINT x;")
    assert output == "8"


def test_store_with_complex_expression() -> None:
    """Test that store definitions can use complex expressions."""
    output: Final = _execute("STORE result = (10 + 5) * 2; PRINT result;")
    assert output == "30"


def test_store_referencing_another_store() -> None:
    """Test that store definitions can reference previously defined stores."""
    output: Final = _execute("STORE a = 10; STORE b = a + 5; PRINT b;")
    assert output == "15"


def test_store_referencing_multiple_stores() -> None:
    """Test that store definitions can reference multiple previously defined stores."""
    output: Final = _execute("STORE x = 3; STORE y = 4; STORE z = x * x + y * y; PRINT z;")
    assert output == "25"


def test_store_with_string_expression() -> None:
    """Test that store definitions can use string expressions."""
    output: Final = _execute("STORE greeting = 'Hello' + ' World'; PRINT greeting;")
    assert output == "Hello World"


def test_store_referencing_store_with_string() -> None:
    """Test that store definitions can reference stores with string values."""
    output: Final = _execute("STORE name = 'Alice'; STORE message = 'Hello, ' + name; PRINT message;")
    assert output == "Hello, Alice"


def test_store_chain_references() -> None:
    """Test that stores can form a chain of references."""
    output: Final = _execute("STORE a = 1; STORE b = a + 1; STORE c = b + 1; STORE d = c + 1; PRINT d;")
    assert output == "4"


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


def test_store_value_persists_after_variable_assignment() -> None:
    """Verify that assigning a store to a variable creates a copy, not a reference."""
    output, store = _execute_with_store("STORE counter = 10; LET x = counter; x = 20; PRINT counter;")
    assert output == "10"  # counter should still be 10
    # Verify the store itself wasn't changed
    key = StoreKey("!test-script", "counter")
    assert store.get_value(key) == NumberValue(value=10.0)


def test_store_assignment_modifies_store() -> None:
    """Verify that directly assigning to a store does modify the store."""
    output, store = _execute_with_store("STORE counter = 10; counter = 20; PRINT counter;")
    assert output == "20"
    # Verify the store was changed
    key = StoreKey("!test-script", "counter")
    assert store.get_value(key) == NumberValue(value=20.0)


def test_store_modification_with_expression() -> None:
    """Verify that modifying a store with an expression updates the store."""
    output, store = _execute_with_store("STORE value = 5; value = value * 3 + 2; PRINT value;")
    assert output == "17"
    # Verify the store was changed
    key = StoreKey("!test-script", "value")
    assert store.get_value(key) == NumberValue(value=17.0)


def test_multiple_store_modifications() -> None:
    """Verify that multiple modifications to a store all persist."""
    output, store = _execute_with_store("STORE x = 1; x = x + 1; x = x + 1; x = x + 1; PRINT x;")
    assert output == "4"
    # Verify the store was changed
    key = StoreKey("!test-script", "x")
    assert store.get_value(key) == NumberValue(value=4.0)


def test_string_store_modification() -> None:
    """Verify that string store modifications persist."""
    output, store = _execute_with_store("STORE msg = 'Hello'; msg = msg + ' World'; PRINT msg;")
    assert output == "Hello World"
    # Verify the store was changed
    key = StoreKey("!test-script", "msg")
    assert store.get_value(key) == StringValue(value="Hello World")


def test_mixed_store_and_variable_assignments() -> None:
    """Verify that stores are modified but variables copied from stores are independent."""
    output, store = _execute_with_store("STORE a = 10; LET b = a; a = 20; b = 30; PRINT a; PRINT b;")
    assert output == "2030"
    # Verify the store 'a' was changed to 20, not affected by variable b
    key = StoreKey("!test-script", "a")
    assert store.get_value(key) == NumberValue(value=20.0)


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
        AssignmentTypeError,
        match="Cannot assign value of type 'string' to target of type 'number'",
    ):
        _execute("LET x = 5; x = 'string';")


def test_print_bool_literals() -> None:
    output: Final = _execute("PRINT true; PRINT false;")
    assert output == "truefalse"


def test_ternary_operator() -> None:
    output = _execute("PRINT true ? 'Greater' : 'Lesser';")
    assert output == "Greater"
    output = _execute("PRINT false ? 'Greater' : 'Lesser';")
    assert output == "Lesser"
    output = _execute("PRINT true ? 42 : 0;")
    assert output == "42"
    output = _execute("PRINT false ? 42 : 0;")
    assert output == "0"


def test_convert_bool_to_number() -> None:
    output: Final = _execute("PRINT $true; PRINT $false;")
    assert output == "10"  # true -> 1, false -> 0


def test_equals_operator() -> None:
    output = _execute("PRINT true == true; PRINT true == false; PRINT false == false;")
    assert output == "truefalsetrue"
    output = _execute("PRINT 5 == 5; PRINT 5 == 10;")
    assert output == "truefalse"
    output = _execute("PRINT 'test' == 'test'; PRINT 'test' == 'TEST';")
    assert output == "truefalse"


def test_not_equals_operator() -> None:
    output = _execute("PRINT true != false; PRINT true != true; PRINT false != false;")
    assert output == "truefalsefalse"
    output = _execute("PRINT 5 != 10; PRINT 5 != 5;")
    assert output == "truefalse"
    output = _execute("PRINT 'test' != 'TEST'; PRINT 'test' != 'test';")
    assert output == "truefalse"


def test_comparison_operators() -> None:
    output = _execute("PRINT 5 < 10; PRINT 10 < 5; PRINT 5 <= 5; PRINT 6 <= 5;")
    assert output == "truefalsetruefalse"
    output = _execute("PRINT 10 > 5; PRINT 5 > 10; PRINT 5 >= 5; PRINT 4 >= 5;")
    assert output == "truefalsetruefalse"
    output = _execute("PRINT 'apple' <= 'banana'; PRINT 'banana' <= 'apple';")
    assert output == "truefalse"
    output = _execute("PRINT 'banana' >= 'apple'; PRINT 'apple' >= 'banana';")
    assert output == "truefalse"
    output = _execute("PRINT 'apple' < 'banana'; PRINT 'banana' < 'apple';")
    assert output == "truefalse"
    output = _execute("PRINT 'banana' > 'apple'; PRINT 'apple' > 'banana';")
    assert output == "truefalse"


def test_logical_operators() -> None:
    output = _execute("PRINT true and true; PRINT true and false; PRINT false and false;")
    assert output == "truefalsefalse"
    output = _execute("PRINT true or false; PRINT false or false; PRINT false or true;")
    assert output == "truefalsetrue"
    output = _execute("PRINT not true; PRINT not false;")
    assert output == "falsetrue"
    output = _execute("PRINT (5 < 10) and (10 < 20); PRINT (5 < 10) and (20 < 10);")
    assert output == "truefalse"
    output = _execute("PRINT (5 > 10) or (10 < 20); PRINT (5 > 10) or (20 < 10);")
    assert output == "truefalse"
