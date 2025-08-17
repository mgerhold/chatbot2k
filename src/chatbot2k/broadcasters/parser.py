import hashlib
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Final

from pydantic import ValidationError

from chatbot2k.broadcasters.broadcaster import Broadcaster
from chatbot2k.broadcasters.simple_broadcaster import SimpleBroadcaster
from chatbot2k.models.broadcasts import BroadcastModel
from chatbot2k.models.broadcasts import BroadcastsModel


def _stable_key(b: BroadcastModel) -> tuple[int, str]:
    # Hash the message (or alias) to avoid depending on input order.
    # Use sha1 -> int for cross-process stability (Python's built-in hash is salted).
    key_src = b.alias_command or b.message
    h = int(hashlib.sha1(key_src.encode("utf-8")).hexdigest(), 16)
    return (h, key_src)


def _build_broadcasters_evenly_spaced(models: Iterable[BroadcastModel]) -> list[Broadcaster]:
    # Group by interval; if your intervals are floats that might differ by tiny epsilons,
    # consider rounding the key, e.g., round(I, 3)
    groups: dict[float, list[BroadcastModel]] = defaultdict(list)
    for m in models:
        groups[m.interval_seconds].append(m)

    broadcasters: list[Broadcaster] = []
    for interval, group in groups.items():
        group_sorted = sorted(group, key=_stable_key)
        n = len(group_sorted)
        if n == 1:
            phase_list = [0.0]
        else:
            # Even phases k*I/n, clamp numerically into [0, I)
            phase_list = [max(0.0, min(interval - 1e-9, (k * interval) / n)) for k in range(n)]

        for m, phase in zip(group_sorted, phase_list, strict=True):
            broadcasters.append(
                SimpleBroadcaster(
                    interval_seconds=interval,
                    message=m.message,
                    phase_offset_seconds=phase,
                    alias_command=m.alias_command,
                )
            )
    return broadcasters


def parse_broadcasters(broadcasters_file_path: Path) -> list[Broadcaster]:
    if not broadcasters_file_path.exists():
        raise FileNotFoundError(f"Broadcasters file not found: {broadcasters_file_path}")
    try:
        contents: Final = broadcasters_file_path.read_text(encoding="utf-8")
    except Exception as e:
        msg: Final = f"Error reading broadcasters file: {broadcasters_file_path}. Error: {e}"
        raise RuntimeError(msg) from e

    try:
        broadcasts: Final = BroadcastsModel.model_validate_json(contents)
    except ValidationError as e:
        msg: Final = f"Error validating commands file: {broadcasters_file_path}. Error: {e}"
        raise RuntimeError(msg) from e

    return _build_broadcasters_evenly_spaced(broadcasts.broadcasts)
