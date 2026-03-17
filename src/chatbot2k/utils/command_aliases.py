from functools import cache
from typing import Final

from greenery import Pattern  # type: ignore[reportMissingTypeStubs]

_MAX_NUM_COMMAND_ALIASES = 3


@cache
def get_aliases(pattern: Pattern) -> tuple[str, ...]:
    # Returns a `tuple` because tuples are immutable and cached values
    # are shared between callers.
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
    return tuple(aliases)
