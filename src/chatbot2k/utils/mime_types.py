from typing import Final
from typing import Optional

import filetype  # type: ignore[reportMissingTypeStubs]

_ALLOWED_MIME_TYPES: Final[dict[str, str]] = {
    "audio/mpeg": ".mp3",
    "audio/x-wav": ".wav",
    "audio/wav": ".wav",
    "audio/ogg": ".ogg",
    "audio/flac": ".flac",
    "audio/aac": ".aac",
    "audio/mp4": ".m4a",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
}


async def get_file_extension_by_mime_type(file_contents: bytes) -> Optional[str]:
    """Detect the MIME type of file contents and return the appropriate file extension.

    Args:
        file_contents: The raw bytes of the file to analyze

    Returns:
        The file extension (including leading dot) if the MIME type is allowed, None otherwise
    """
    kind: Final = filetype.guess(file_contents)  # type: ignore[reportUnknownMemberType]
    if kind is None or kind.mime not in _ALLOWED_MIME_TYPES:
        return None

    mime: Final = kind.mime  # type: ignore[reportUnknownMemberType]
    if not isinstance(mime, str):
        raise AssertionError

    return _ALLOWED_MIME_TYPES[mime]
