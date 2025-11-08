from typing import NamedTuple
from typing import final

from chatbot2k.scripting_engine.source_location import SourceLocation
from chatbot2k.scripting_engine.token_types import TokenType


@final
class Token(NamedTuple):
    type: TokenType
    source_location: SourceLocation
