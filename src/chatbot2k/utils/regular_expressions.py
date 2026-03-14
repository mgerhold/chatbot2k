from functools import lru_cache

from greenery import Pattern  # type: ignore[reportMissingTypeStubs]
from greenery import parse  # type: ignore[reportMissingTypeStubs]


@lru_cache
def parse_regular_expression(name: str) -> Pattern:
    """
    Parses a regular expression pattern from the given name. To avoid
    case sensitivity issues, the name is converted to lowercase before parsing.
    """
    return parse(name.lower())
