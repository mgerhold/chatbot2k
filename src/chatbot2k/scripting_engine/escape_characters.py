"""Escape character mappings for the scripting language."""

from typing import Final

ESCAPE_CHARACTERS: Final[dict[str, str]] = {
    "n": "\n",
    "'": "'",
    "\\": "\\",
}
