from datetime import UTC
from datetime import datetime
from typing import Optional

from chatbot2k.constants import SOUNDBOARD_FILES_DIRECTORY
from chatbot2k.types.template_contexts import SortOrder


def get_soundboard_clip_uploaded_at(filename: str) -> Optional[datetime]:
    """Returns the clip file's last-modified time as a proxy for its upload date."""
    try:
        return datetime.fromtimestamp((SOUNDBOARD_FILES_DIRECTORY / filename).stat().st_mtime, tz=UTC)
    except OSError:
        # The clip file is missing on disk even though the database row (or handler) exists.
        return None


def sort_order_to_reverse(order: SortOrder) -> bool:
    """Converts a `SortOrder` into the `reverse` argument expected by `sorted()`."""
    match order:
        case SortOrder.ASC:
            return False
        case SortOrder.DESC:
            return True
