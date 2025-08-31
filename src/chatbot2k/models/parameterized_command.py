from typing import NamedTuple
from typing import final


@final
class ParameterizedCommand(NamedTuple):
    """
    Helper type to work around the fact that SQLModel does not automatically fetch
    related objects (via foreign key) when querying the database.
    """

    name: str
    response: str
    parameters: list[str]
