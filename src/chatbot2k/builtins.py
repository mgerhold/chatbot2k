from collections.abc import Callable
from datetime import datetime
from enum import Enum
from enum import auto
from typing import Final
from typing import final
from zoneinfo import ZoneInfo

from babel.dates import format_date
from babel.dates import format_time

from chatbot2k.app_state import AppState
from chatbot2k.types.configuration_setting_kind import ConfigurationSettingKind


def _get_timezone_and_locale(app_state: AppState) -> tuple[ZoneInfo, str]:
    timezone: Final = ZoneInfo(
        app_state.database.retrieve_configuration_setting_or_default(
            ConfigurationSettingKind.TIMEZONE,
            "UTC",
        )
    )
    locale: Final = app_state.database.retrieve_configuration_setting_or_default(
        ConfigurationSettingKind.LOCALE,
        "en_US.UTF-8",
    )
    return timezone, locale


def _get_current_time(app_state: AppState) -> str:
    timezone, locale = _get_timezone_and_locale(app_state)
    now: Final = datetime.now(timezone)
    return format_time(now, tzinfo=timezone, locale=locale)


def _get_current_date(app_state: AppState) -> str:
    timezone, locale = _get_timezone_and_locale(app_state)
    now: Final = datetime.now(timezone)
    return format_date(now.date(), locale=locale)


@final
class Builtin(Enum):
    CURRENT_TIME = auto()
    CURRENT_DATE = auto()


BUILTINS: dict[Builtin, Callable[[AppState], str]] = {
    Builtin.CURRENT_TIME: _get_current_time,
    Builtin.CURRENT_DATE: _get_current_date,
}


def apply_builtins(text: str, app_state: AppState) -> str:
    for builtin, func in BUILTINS.items():
        text = text.replace(f"{{{builtin.name}}}", func(app_state))
    return text
