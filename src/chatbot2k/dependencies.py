from functools import lru_cache
from pathlib import Path
from typing import Annotated
from typing import Final
from typing import NamedTuple
from typing import Optional
from typing import final

import jwt
from fastapi import Depends
from starlette.requests import Request
from starlette.templating import Jinja2Templates

from chatbot2k.app_state import AppState
from chatbot2k.globals import Globals
from chatbot2k.routes.auth_constants import JWT_ALG
from chatbot2k.routes.auth_constants import SESSION_COOKIE


@final
class UserInfo(NamedTuple):
    id: str
    login: str
    display_name: str


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


def get_current_user(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
) -> Optional[UserInfo]:
    """Extract user information from JWT cookie if present and valid."""
    session_token: Final = request.cookies.get(SESSION_COOKIE)
    if session_token is None:
        return None

    try:
        payload: Final = jwt.decode(  # type: ignore[reportUnknownMemberType]
            jwt=session_token,
            key=app_state.config.jwt_secret,
            algorithms=[JWT_ALG],
        )
        return UserInfo(
            id=payload.get("sub"),
            login=payload.get("login"),
            display_name=payload.get("display_name"),
        )
    except (jwt.InvalidTokenError, KeyError):
        return None
