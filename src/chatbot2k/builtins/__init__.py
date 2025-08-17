from collections.abc import Callable
from datetime import datetime
from enum import Enum
from enum import auto
from typing import Final
from typing import final

from babel.dates import format_datetime

from chatbot2k.config import CONFIG


def _get_current_time() -> str:
    now: Final = datetime.now(CONFIG.timezone)
    return format_datetime(now, tzinfo=CONFIG.timezone, locale=CONFIG.locale)


@final
class Builtin(Enum):
    CURRENT_TIME = auto()


BUILTINS: dict[Builtin, Callable[[], str]] = {Builtin.CURRENT_TIME: _get_current_time}


def apply_builtins(text: str) -> str:
    for builtin, func in BUILTINS.items():
        text = text.replace(f"{{{builtin.name}}}", func())
    return text
