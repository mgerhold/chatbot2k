from typing import NamedTuple
from typing import final

from greenery import Pattern  # type: ignore[reportMissingTypeStubs]

from chatbot2k.utils.regular_expressions import parse_regular_expression


@final
class ParameterizedCommand(NamedTuple):
    """
    Helper type to work around the fact that SQLModel does not automatically fetch
    related objects (via foreign key) when querying the database.
    """

    name: str
    response: str
    parameters: list[str]

    @property
    def regular_expression(self) -> Pattern:
        return parse_regular_expression(self.name)
