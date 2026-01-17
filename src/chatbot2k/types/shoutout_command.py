from typing import NamedTuple
from typing import final


@final
class ShoutoutCommand(NamedTuple):
    from_broadcaster_id: str
    to_broadcaster_id: str
