from functools import lru_cache
from pathlib import Path
from typing import Final

from starlette.templating import Jinja2Templates

from chatbot2k.app_state import AppState
from chatbot2k.globals import Globals


@lru_cache
def get_app_state() -> AppState:
    # Returns a singleton instance of `Globals` which implements
    # the `AppState` interface.
    return Globals()


@lru_cache
def get_templates() -> Jinja2Templates:
    templates_path: Final = Path(__file__).parent.parent.parent / "templates"
    if not templates_path.exists():
        raise FileNotFoundError(f"Templates directory not found: {templates_path}")
    return Jinja2Templates(templates_path)
