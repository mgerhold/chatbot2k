from functools import cache

from greenery import Pattern  # type: ignore[reportMissingTypeStubs]
from greenery import parse  # type: ignore[reportMissingTypeStubs]


@cache
def parse_regular_expression(name: str) -> Pattern:
    """
    Parses a regular expression pattern from the given name. To avoid
    case sensitivity issues, the name is converted to lowercase before parsing.
    """
    return parse(name.lower())


@cache
def is_regex_pattern(pattern: Pattern) -> bool:
    """
    Returns `True` if the pattern matches more than one distinct string, i.e. it
    behaves as a genuine regular expression rather than a plain constant trigger.

    The check generates at most two candidate strings from the pattern and stops
    as soon as a second one is found, so it is very cheap for the common case of
    plain string triggers. The result is cached because Pattern objects returned
    by `parse_regular_expression()` are themselves cached (same name → same object).
    """
    return len(list(zip(range(2), pattern.strings(), strict=False))) > 1
