from typing import Final

from greenery import Pattern  # type: ignore[reportMissingTypeStubs]

_MAX_NUM_COMMAND_ALIASES = 3


def get_aliases(pattern: Pattern) -> list[str]:
    aliases: Final = sorted(
        f"!{alias}"
        for _, alias in zip(
            range(_MAX_NUM_COMMAND_ALIASES + 1),
            pattern.strings(),
            strict=False,
        )
    )
    if len(aliases) > _MAX_NUM_COMMAND_ALIASES:
        aliases[-1] = "!..."
    return aliases
