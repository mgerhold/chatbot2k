from pathlib import Path

STATIC_FILES_DIRECTORY = Path(__file__).parent.parent.parent / "static"
SOUNDBOARD_FILES_DIRECTORY = STATIC_FILES_DIRECTORY / "soundboard"
# The following version is relative to the web server root.
RELATIVE_SOUNDBOARD_FILES_DIRECTORY = Path("static") / "soundboard"
