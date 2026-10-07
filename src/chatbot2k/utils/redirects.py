from typing import Final
from typing import Optional
from urllib.parse import urlsplit

# Redirecting to these paths after logging in makes no sense (or would e.g. log the user out again).
_EXCLUDED_PATH_PREFIXES: Final = ("/login", "/auth/")


def get_safe_redirect_target(target: Optional[str]) -> Optional[str]:
    """Returns `target` if it is a path on this site (e.g. `/viewer/soundboard?tab=upload`) that is
    safe to redirect to after logging in, otherwise `None`.

    This prevents open redirects, i.e. redirects to other sites such as `https://evil.example`
    or `//evil.example`.
    """
    if target is None or not target.startswith("/") or target.startswith("//"):
        return None
    # Browsers treat backslashes like slashes (`/\evil.example` => `//evil.example`), and control
    # characters may be stripped by them.
    if "\\" in target or any(ord(char) < 0x20 or ord(char) == 0x7F for char in target):
        return None
    parts: Final = urlsplit(target)
    if parts.scheme or parts.netloc:
        return None
    if parts.path.startswith(_EXCLUDED_PATH_PREFIXES):
        return None
    return target
