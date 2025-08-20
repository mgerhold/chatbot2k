from collections.abc import Callable
from datetime import datetime
from enum import Enum
from enum import auto
from typing import Final
from typing import final

from babel.dates import format_date
from babel.dates import format_time

from chatbot2k.config import Config


def _get_current_time(config: Config) -> str:
    now: Final = datetime.now(config.timezone)
    return format_time(now, tzinfo=config.timezone, locale=config.locale)


def _get_current_date(config: Config) -> str:
    now: Final = datetime.now(config.timezone)
    return format_date(now.date(), locale=config.locale)


@final
class Builtin(Enum):
    CURRENT_TIME = auto()
    CURRENT_DATE = auto()


BUILTINS: dict[Builtin, Callable[[Config], str]] = {
    Builtin.CURRENT_TIME: _get_current_time,
    Builtin.CURRENT_DATE: _get_current_date,
}


def apply_builtins(text: str, config: Config) -> str:
    for builtin, func in BUILTINS.items():
        text = text.replace(f"{{{builtin.name}}}", func(config))
    return text
