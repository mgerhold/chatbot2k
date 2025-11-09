from typing import Final

import pytest

from chatbot2k.scripting_engine.lexer import Lexer
from chatbot2k.scripting_engine.parser import Parser
from chatbot2k.scripting_engine.types import NumberLiteralExpression
from chatbot2k.scripting_engine.types import PrintStatement
from chatbot2k.scripting_engine.types import Script
from chatbot2k.scripting_engine.types import StringLiteralExpression


def _parse_source(source: str) -> Script:
    lexer: Final = Lexer(source)
    tokens: Final = lexer.tokenize()
    parser: Final = Parser(tokens)
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
        ("PRINT -17;", -17.0),
        ("PRINT -999;", -999.0),
        ("PRINT 3.14;", 3.14),
        ("PRINT -2.5;", -2.5),
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
