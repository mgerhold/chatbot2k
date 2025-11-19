from typing import Final

import pytest

from chatbot2k.scripting_engine.lexer import Lexer
from chatbot2k.scripting_engine.parser import DuplicateParameterNameError
from chatbot2k.scripting_engine.parser import ExpectedTokenError
from chatbot2k.scripting_engine.parser import ParameterShadowsStoreError
from chatbot2k.scripting_engine.parser import Parser
from chatbot2k.scripting_engine.parser import StoreRedefinitionError
from chatbot2k.scripting_engine.parser import UnknownVariableError
from chatbot2k.scripting_engine.parser import VariableRedefinitionError
from chatbot2k.scripting_engine.parser import VariableShadowsParameterError
from chatbot2k.scripting_engine.parser import VariableShadowsStoreError
from chatbot2k.scripting_engine.types.ast import Script
from chatbot2k.scripting_engine.types.data_types import DataType
from chatbot2k.scripting_engine.types.expressions import BinaryOperationExpression
from chatbot2k.scripting_engine.types.expressions import BinaryOperator
from chatbot2k.scripting_engine.types.expressions import NumberLiteralExpression
from chatbot2k.scripting_engine.types.expressions import StoreIdentifierExpression
from chatbot2k.scripting_engine.types.expressions import StringLiteralExpression
from chatbot2k.scripting_engine.types.expressions import UnaryOperationExpression
from chatbot2k.scripting_engine.types.expressions import UnaryOperator
from chatbot2k.scripting_engine.types.statements import PrintStatement
from chatbot2k.scripting_engine.types.statements import VariableDefinitionStatement


def _parse_source(source: str) -> Script:
    lexer: Final = Lexer(source)
    tokens: Final = lexer.tokenize()
    parser: Final = Parser("!some_script_name", tokens)
    return parser.parse()


@pytest.mark.parametrize(
    ("source", "expected_value"),
    [
        ("PRINT 'Hello, World!';", "Hello, World!"),
        (r"PRINT 'Line 1\nLine 2';", "Line 1\nLine 2"),
        (r"PRINT 'in \'quotes\' is it';", "in 'quotes' is it"),
        ("PRINT 5;", 5.0),
        ("PRINT 42;", 42.0),
        ("PRINT 123;", 123.0),
        ("PRINT 0;", 0.0),
        ("PRINT 3.14;", 3.14),
        ("PRINT 0.0;", 0.0),
    ],
)
def test_parser_parses_print_statement(source: str, expected_value: str | float) -> None:
    script: Final = _parse_source(source)
    assert not script.stores
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(argument=StringLiteralExpression(value=value)):
            assert value == expected_value
        case PrintStatement(argument=NumberLiteralExpression(value=value)):
            assert value == expected_value
        case _:
            pytest.fail(f"Unexpected statement type: {type(script.statements[0])}")


def test_parser_parses_stores() -> None:
    script: Final = _parse_source("STORE fizzle = 0; STORE wizzle = 'chizzle'; PRINT fizzle; PRINT wizzle;")
    assert len(script.stores) == 2
    assert script.stores[0].name == "fizzle"
    assert script.stores[0].data_type == DataType.NUMBER
    assert isinstance(script.stores[0].value, NumberLiteralExpression)
    assert script.stores[0].value.value == 0.0
    assert script.stores[1].name == "wizzle"
    assert script.stores[1].data_type == DataType.STRING
    assert isinstance(script.stores[1].value, StringLiteralExpression)
    assert script.stores[1].value.value == "chizzle"
    assert len(script.statements) == 2


def test_parser_parses_store_with_expression() -> None:
    """Test that stores can be initialized with expressions."""
    script: Final = _parse_source("STORE result = 5 + 3; PRINT result;")
    assert len(script.stores) == 1
    assert script.stores[0].name == "result"
    assert script.stores[0].data_type == DataType.NUMBER
    assert isinstance(script.stores[0].value, BinaryOperationExpression)
    assert script.stores[0].value.operator == BinaryOperator.ADD


def test_parser_parses_store_referencing_another_store() -> None:
    """Test that stores can reference previously defined stores."""
    script: Final = _parse_source("STORE a = 10; STORE b = a + 5; PRINT b;")
    assert len(script.stores) == 2
    assert script.stores[0].name == "a"
    assert isinstance(script.stores[0].value, NumberLiteralExpression)
    assert script.stores[1].name == "b"
    assert isinstance(script.stores[1].value, BinaryOperationExpression)
    # Verify the expression references store 'a'
    match script.stores[1].value:
        case BinaryOperationExpression(
            operator=BinaryOperator.ADD,
            left=StoreIdentifierExpression(store_name="a"),
            right=NumberLiteralExpression(value=5.0),
        ):
            pass  # Test passes
        case _:
            pytest.fail(f"Unexpected store expression: {script.stores[1].value}")


def test_parser_parses_variable_definitions() -> None:
    script: Final = _parse_source("LET i = 0; LET message = 'test'; PRINT i; PRINT message;")
    assert len(script.stores) == 0
    assert len(script.statements) == 4
    assert isinstance(script.statements[0], VariableDefinitionStatement)
    assert script.statements[0].variable_name == "i"
    assert isinstance(script.statements[0].initial_value, NumberLiteralExpression)
    assert script.statements[0].initial_value.value == 0.0
    assert isinstance(script.statements[1], VariableDefinitionStatement)
    assert script.statements[1].variable_name == "message"
    assert isinstance(script.statements[1].initial_value, StringLiteralExpression)
    assert script.statements[1].initial_value.value == "test"


def test_parser_raises_on_redefinition_of_store() -> None:
    with pytest.raises(StoreRedefinitionError, match="Store 'my_store' is already defined."):
        _parse_source("STORE my_store = 5; STORE my_store = 'duplicate';")


def test_parser_raises_on_redefinition_of_variable() -> None:
    with pytest.raises(VariableRedefinitionError, match="Variable 'my_var' is already defined."):
        _parse_source("LET my_var = 10; LET my_var = 20;")


def test_parser_raises_on_unknown_variable() -> None:
    with pytest.raises(UnknownVariableError, match="Variable 'unknown_var' is not defined."):
        _parse_source("PRINT unknown_var;")


def test_parser_parses_binary_operations() -> None:
    script: Final = _parse_source("PRINT 1 + 2;")
    assert len(script.statements) == 1
    print_stmt: Final = script.statements[0]
    assert isinstance(print_stmt, PrintStatement)
    argument: Final = print_stmt.argument
    assert isinstance(argument, BinaryOperationExpression)
    assert argument.operator == BinaryOperator.ADD
    assert isinstance(argument.left, NumberLiteralExpression)
    assert argument.left.value == 1.0
    assert isinstance(argument.right, NumberLiteralExpression)
    assert argument.right.value == 2.0


@pytest.mark.parametrize(
    ("source", "operator", "left_value", "right_value"),
    [
        ("PRINT 10 + 5;", BinaryOperator.ADD, 10.0, 5.0),
        ("PRINT 10 - 5;", BinaryOperator.SUBTRACT, 10.0, 5.0),
        ("PRINT 10 * 5;", BinaryOperator.MULTIPLY, 10.0, 5.0),
        ("PRINT 10 / 5;", BinaryOperator.DIVIDE, 10.0, 5.0),
        ("PRINT 3.14 + 2.86;", BinaryOperator.ADD, 3.14, 2.86),
        ("PRINT 0 - 10;", BinaryOperator.SUBTRACT, 0.0, 10.0),
        ("PRINT 100 / 2.5;", BinaryOperator.DIVIDE, 100.0, 2.5),
    ],
)
def test_parser_parses_number_binary_operations(
    source: str,
    operator: BinaryOperator,
    left_value: float,
    right_value: float,
) -> None:
    script: Final = _parse_source(source)
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=BinaryOperationExpression(
                operator=op,
                left=NumberLiteralExpression(value=left),
                right=NumberLiteralExpression(value=right),
            )
        ):
            assert op == operator
            assert left == left_value
            assert right == right_value
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


@pytest.mark.parametrize(
    ("source", "left_value", "right_value"),
    [
        ("PRINT 'Hello, ' + 'World!';", "Hello, ", "World!"),
        ("PRINT 'foo' + 'bar';", "foo", "bar"),
        ("PRINT '' + 'test';", "", "test"),
    ],
)
def test_parser_parses_string_concatenation(source: str, left_value: str, right_value: str) -> None:
    script: Final = _parse_source(source)
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=BinaryOperationExpression(
                operator=BinaryOperator.ADD,
                left=StringLiteralExpression(value=left),
                right=StringLiteralExpression(value=right),
            )
        ):
            assert left == left_value
            assert right == right_value
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_respects_multiplication_precedence_over_addition() -> None:
    # 2 + 3 * 4 should be parsed as 2 + (3 * 4)
    script: Final = _parse_source("PRINT 2 + 3 * 4;")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=BinaryOperationExpression(
                operator=BinaryOperator.ADD,
                left=NumberLiteralExpression(value=2.0),
                right=BinaryOperationExpression(
                    operator=BinaryOperator.MULTIPLY,
                    left=NumberLiteralExpression(value=3.0),
                    right=NumberLiteralExpression(value=4.0),
                ),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_respects_division_precedence_over_subtraction() -> None:
    # 10 - 8 / 2 should be parsed as 10 - (8 / 2)
    script: Final = _parse_source("PRINT 10 - 8 / 2;")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=BinaryOperationExpression(
                operator=BinaryOperator.SUBTRACT,
                left=NumberLiteralExpression(value=10.0),
                right=BinaryOperationExpression(
                    operator=BinaryOperator.DIVIDE,
                    left=NumberLiteralExpression(value=8.0),
                    right=NumberLiteralExpression(value=2.0),
                ),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_respects_left_associativity_for_addition() -> None:
    # 1 + 2 + 3 should be parsed as (1 + 2) + 3
    script: Final = _parse_source("PRINT 1 + 2 + 3;")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=BinaryOperationExpression(
                operator=BinaryOperator.ADD,
                left=BinaryOperationExpression(
                    operator=BinaryOperator.ADD,
                    left=NumberLiteralExpression(value=1.0),
                    right=NumberLiteralExpression(value=2.0),
                ),
                right=NumberLiteralExpression(value=3.0),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_respects_left_associativity_for_multiplication() -> None:
    # 2 * 3 * 4 should be parsed as (2 * 3) * 4
    script: Final = _parse_source("PRINT 2 * 3 * 4;")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=BinaryOperationExpression(
                operator=BinaryOperator.MULTIPLY,
                left=BinaryOperationExpression(
                    operator=BinaryOperator.MULTIPLY,
                    left=NumberLiteralExpression(value=2.0),
                    right=NumberLiteralExpression(value=3.0),
                ),
                right=NumberLiteralExpression(value=4.0),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_respects_complex_precedence() -> None:
    # 1 + 2 * 3 - 4 / 2 should be parsed as (1 + (2 * 3)) - (4 / 2)
    script: Final = _parse_source("PRINT 1 + 2 * 3 - 4 / 2;")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=BinaryOperationExpression(
                operator=BinaryOperator.SUBTRACT,
                left=BinaryOperationExpression(
                    operator=BinaryOperator.ADD,
                    left=NumberLiteralExpression(value=1.0),
                    right=BinaryOperationExpression(
                        operator=BinaryOperator.MULTIPLY,
                        left=NumberLiteralExpression(value=2.0),
                        right=NumberLiteralExpression(value=3.0),
                    ),
                ),
                right=BinaryOperationExpression(
                    operator=BinaryOperator.DIVIDE,
                    left=NumberLiteralExpression(value=4.0),
                    right=NumberLiteralExpression(value=2.0),
                ),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_handles_mixed_operators_with_same_precedence() -> None:
    # 10 - 5 + 3 should be parsed as (10 - 5) + 3 (left-associative)
    script: Final = _parse_source("PRINT 10 - 5 + 3;")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=BinaryOperationExpression(
                operator=BinaryOperator.ADD,
                left=BinaryOperationExpression(
                    operator=BinaryOperator.SUBTRACT,
                    left=NumberLiteralExpression(value=10.0),
                    right=NumberLiteralExpression(value=5.0),
                ),
                right=NumberLiteralExpression(value=3.0),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_handles_division_and_multiplication_left_to_right() -> None:
    # 20 / 4 * 2 should be parsed as (20 / 4) * 2 (left-associative)
    script: Final = _parse_source("PRINT 20 / 4 * 2;")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=BinaryOperationExpression(
                operator=BinaryOperator.MULTIPLY,
                left=BinaryOperationExpression(
                    operator=BinaryOperator.DIVIDE,
                    left=NumberLiteralExpression(value=20.0),
                    right=NumberLiteralExpression(value=4.0),
                ),
                right=NumberLiteralExpression(value=2.0),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_parses_unary_plus() -> None:
    # +5 should be parsed as UnaryOperation(PLUS, 5)
    script: Final = _parse_source("PRINT +5;")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=UnaryOperationExpression(
                operator=UnaryOperator.PLUS,
                operand=NumberLiteralExpression(value=5.0),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_parses_unary_minus() -> None:
    # -(5) should be parsed as unary minus applied to 5
    script: Final = _parse_source("PRINT -(5);")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=UnaryOperationExpression(
                operator=UnaryOperator.NEGATE,
                operand=NumberLiteralExpression(value=5.0),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_parses_unary_minus_with_negative_literal() -> None:
    # --5 should now be parsed as UnaryOperation(NEGATE, UnaryOperation(NEGATE, NumberLiteral(5)))
    # because -5 is no longer a negative number literal
    script: Final = _parse_source("PRINT --5;")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=UnaryOperationExpression(
                operator=UnaryOperator.NEGATE,
                operand=UnaryOperationExpression(
                    operator=UnaryOperator.NEGATE,
                    operand=NumberLiteralExpression(value=5.0),
                ),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_parses_negative_literal_in_parentheses() -> None:
    # (-5) should be parsed as unary minus applied to 5
    script: Final = _parse_source("PRINT (-5);")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=UnaryOperationExpression(
                operator=UnaryOperator.NEGATE,
                operand=NumberLiteralExpression(value=5.0),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_parses_double_negation() -> None:
    # -(-(5)) should be parsed as UnaryOperation(NEGATE, UnaryOperation(NEGATE, 5))
    script: Final = _parse_source("PRINT -(-(5));")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=UnaryOperationExpression(
                operator=UnaryOperator.NEGATE,
                operand=UnaryOperationExpression(
                    operator=UnaryOperator.NEGATE,
                    operand=NumberLiteralExpression(value=5.0),
                ),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_parses_string_to_number_operator_with_string_literal() -> None:
    # $'42' should be parsed as UnaryOperation(TO_NUMBER, StringLiteral('42'))
    script: Final = _parse_source("PRINT $'42';")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=UnaryOperationExpression(
                operator=UnaryOperator.TO_NUMBER,
                operand=StringLiteralExpression(value="42"),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_parses_string_to_number_operator_with_string_expression() -> None:
    # $('3' + '.14') should be parsed correctly
    script: Final = _parse_source("PRINT $('3' + '.14');")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=UnaryOperationExpression(
                operator=UnaryOperator.TO_NUMBER,
                operand=BinaryOperationExpression(
                    operator=BinaryOperator.ADD,
                    left=StringLiteralExpression(value="3"),
                    right=StringLiteralExpression(value=".14"),
                ),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_parses_string_to_number_operator_with_store() -> None:
    # $my_store should be parsed as UnaryOperation(TO_NUMBER, StoreIdentifier('my_store'))
    script: Final = _parse_source("STORE my_store = '123'; PRINT $my_store;")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=UnaryOperationExpression(
                operator=UnaryOperator.TO_NUMBER,
                operand=StoreIdentifierExpression(store_name="my_store"),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_parses_evaluate_operator_with_string_literal() -> None:
    # !'PRINT 5;' should be parsed as UnaryOperation(EVALUATE, StringLiteral('PRINT 5;'))
    script: Final = _parse_source("PRINT !'PRINT 5;';")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=UnaryOperationExpression(
                operator=UnaryOperator.EVALUATE,
                operand=StringLiteralExpression(value="PRINT 5;"),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_parses_evaluate_operator_with_string_expression() -> None:
    # !('PRINT ' + '42;') should be parsed correctly
    script: Final = _parse_source("PRINT !('PRINT ' + '42;');")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=UnaryOperationExpression(
                operator=UnaryOperator.EVALUATE,
                operand=BinaryOperationExpression(
                    operator=BinaryOperator.ADD,
                    left=StringLiteralExpression(value="PRINT "),
                    right=StringLiteralExpression(value="42;"),
                ),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_parses_evaluate_operator_with_store() -> None:
    # !code_store should be parsed as UnaryOperation(EVALUATE, StoreIdentifier('code_store'))
    script: Final = _parse_source("STORE code_store = 'PRINT 100;'; PRINT !code_store;")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=UnaryOperationExpression(
                operator=UnaryOperator.EVALUATE,
                operand=StoreIdentifierExpression(store_name="code_store"),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_parses_grouped_expression() -> None:
    # (5) should just return the number
    script: Final = _parse_source("PRINT (5);")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(argument=NumberLiteralExpression(value=5.0)):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_parses_grouped_expression_with_operation() -> None:
    # (2 + 3) should be parsed as a binary operation
    script: Final = _parse_source("PRINT (2 + 3);")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=BinaryOperationExpression(
                operator=BinaryOperator.ADD,
                left=NumberLiteralExpression(value=2.0),
                right=NumberLiteralExpression(value=3.0),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_respects_parentheses_for_precedence() -> None:
    # (2 + 3) * 4 should be parsed as (2 + 3) * 4, not 2 + (3 * 4)
    script: Final = _parse_source("PRINT (2 + 3) * 4;")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=BinaryOperationExpression(
                operator=BinaryOperator.MULTIPLY,
                left=BinaryOperationExpression(
                    operator=BinaryOperator.ADD,
                    left=NumberLiteralExpression(value=2.0),
                    right=NumberLiteralExpression(value=3.0),
                ),
                right=NumberLiteralExpression(value=4.0),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_handles_nested_parentheses() -> None:
    # ((5)) should just return the number
    script: Final = _parse_source("PRINT ((5));")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(argument=NumberLiteralExpression(value=5.0)):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_handles_complex_expression_with_parentheses_and_unary() -> None:
    # -(2 + 3) * 4 should be parsed as (-(2 + 3)) * 4
    script: Final = _parse_source("PRINT -(2 + 3) * 4;")
    assert len(script.statements) == 1

    match script.statements[0]:
        case PrintStatement(
            argument=BinaryOperationExpression(
                operator=BinaryOperator.MULTIPLY,
                left=UnaryOperationExpression(
                    operator=UnaryOperator.NEGATE,
                    operand=BinaryOperationExpression(
                        operator=BinaryOperator.ADD,
                        left=NumberLiteralExpression(value=2.0),
                        right=NumberLiteralExpression(value=3.0),
                    ),
                ),
                right=NumberLiteralExpression(value=4.0),
            )
        ):
            pass  # Test passed
        case _:
            pytest.fail(f"Unexpected statement structure: {script.statements[0]}")


def test_parser_parses_no_parameters() -> None:
    """Test that a script without parameters works correctly."""
    script: Final = _parse_source("PRINT 'no params';")
    assert len(script.stores) == 0
    assert len(script.parameters) == 0
    assert len(script.statements) == 1


def test_parser_parses_single_parameter() -> None:
    """Test parsing a script with a single parameter."""
    script: Final = _parse_source("PARAMS my_param; PRINT 'test';")
    assert len(script.parameters) == 1
    assert script.parameters[0].name == "my_param"


def test_parser_parses_multiple_parameters() -> None:
    """Test parsing a script with multiple parameters."""
    script: Final = _parse_source("PARAMS first, second, third; PRINT 'test';")
    assert len(script.parameters) == 3
    assert script.parameters[0].name == "first"
    assert script.parameters[1].name == "second"
    assert script.parameters[2].name == "third"


def test_parser_parses_two_parameters() -> None:
    """Test parsing a script with exactly two parameters."""
    script: Final = _parse_source("PARAMS alpha, beta; PRINT 'test';")
    assert len(script.parameters) == 2
    assert script.parameters[0].name == "alpha"
    assert script.parameters[1].name == "beta"


def test_parser_parses_parameters_with_stores() -> None:
    """Test that parameters can be used together with stores."""
    script: Final = _parse_source("STORE counter = 0; PARAMS user_id; PRINT counter;")
    assert len(script.parameters) == 1
    assert script.parameters[0].name == "user_id"
    assert len(script.stores) == 1
    assert script.stores[0].name == "counter"


def test_parser_does_not_allow_parameters_before_stores() -> None:
    """Test that stores must come before parameters."""
    with pytest.raises(ExpectedTokenError, match="Expected statement"):
        _ = _parse_source("PARAMS name; STORE value = 42; PRINT value;")


def test_parser_raises_on_duplicate_parameter_names() -> None:
    """Test that duplicate parameter names raise an error."""
    with pytest.raises(DuplicateParameterNameError, match="Parameter 'duplicate' is already defined."):
        _parse_source("PARAMS duplicate, duplicate; PRINT 'test';")


def test_parser_raises_on_duplicate_parameter_in_longer_list() -> None:
    """Test that duplicate parameter names are caught even in longer lists."""
    with pytest.raises(DuplicateParameterNameError, match="Parameter 'second' is already defined."):
        _parse_source("PARAMS first, second, third, second; PRINT 'test';")


def test_parser_parses_trailing_comma_in_parameters() -> None:
    """Test that trailing comma before semicolon is handled."""
    script: Final = _parse_source("PARAMS param1, param2,; PRINT 'test';")
    assert len(script.parameters) == 2
    assert script.parameters[0].name == "param1"
    assert script.parameters[1].name == "param2"


def test_parser_allows_parameter_names_similar_to_keywords() -> None:
    """Test that parameter names can be similar to keywords (but not exact matches)."""
    script: Final = _parse_source("PARAMS store, print, let; PRINT 'test';")
    assert len(script.parameters) == 3
    assert script.parameters[0].name == "store"
    assert script.parameters[1].name == "print"
    assert script.parameters[2].name == "let"


def test_parser_does_not_allow_parameter_name_identical_to_store_name() -> None:
    """Test that a parameter name identical to a store name raises an error."""
    with pytest.raises(
        ParameterShadowsStoreError,
        match="Parameter 'data' shadows store with the same name.",
    ):
        _parse_source("STORE data = 100; PARAMS data; PRINT data;")


def test_parser_does_not_allow_variable_name_identical_to_parameter_name() -> None:
    """Test that a variable name identical to a parameter name raises an error."""
    with pytest.raises(
        VariableShadowsParameterError,
        match="Variable 'input' shadows parameter with the same name.",
    ):
        _parse_source("PARAMS input; LET input = 5; PRINT input;")


def test_parser_does_not_allow_variable_name_identical_to_store_name() -> None:
    """Test that a variable name identical to a store name raises an error."""
    with pytest.raises(
        VariableShadowsStoreError,
        match="Variable 'config' shadows store with the same name.",
    ):
        _parse_source("STORE config = 'value'; LET config = 10; PRINT config;")
