from types import SimpleNamespace
from typing import Final
from typing import NoReturn
from typing import Optional
from typing import cast
from typing import final

import jwt
import pytest
from starlette.requests import Request
from twitchAPI.type import InvalidRefreshTokenException

from chatbot2k.app_state import AppState
from chatbot2k.config import Config
from chatbot2k.database.tables import TwitchTokenSet
from chatbot2k.dependencies import get_common_context
from chatbot2k.dependencies import get_current_user
from chatbot2k.routes.auth_constants import JWT_ALG
from chatbot2k.routes.auth_constants import SESSION_COOKIE
from chatbot2k.types.configuration_setting_kind import ConfigurationSettingKind
from chatbot2k.utils import auth


@final
class _FakeDatabase:
    # `Database` is final and needs migrations to instantiate, so this mirrors
    # the signatures of the methods used by the dependencies under test.
    def __init__(self, token_set: Optional[TwitchTokenSet] = None) -> None:
        self._token_set: Final = token_set

    def get_twitch_token_set(self, *, user_id: str) -> Optional[TwitchTokenSet]:
        return self._token_set

    def get_number_of_pending_soundboard_clips(self) -> int:
        return 0

    def retrieve_configuration_setting_or_default[T](self, kind: ConfigurationSettingKind, default: T) -> str | T:
        return default


def _app_state(database: _FakeDatabase) -> AppState:
    return cast(AppState, SimpleNamespace(config=Config(), database=database))


def _session_jwt(config: Config, user_id: str) -> str:
    return jwt.encode(  # type: ignore[reportUnknownMemberType]
        {"sub": user_id, "login": "alice", "display_name": "Alice"},
        config.jwt_secret,
        algorithm=JWT_ALG,
    )


def _request_with_session_cookie(token: str) -> Request:
    return Request(
        scope={
            "type": "http",
            "headers": [(b"cookie", f"{SESSION_COOKIE}={token}".encode())],
        }
    )


def _token_set(user_id: str) -> TwitchTokenSet:
    return TwitchTokenSet(user_id=user_id, access_token="access", refresh_token="refresh", expires_at=0)


def test_valid_jwt_without_token_row_is_logged_out() -> None:
    # Logout on another device deletes the token row while this cookie stays valid.
    app_state: Final = _app_state(_FakeDatabase(token_set=None))
    request: Final = _request_with_session_cookie(_session_jwt(app_state.config, "12345"))

    assert get_current_user(request, app_state) is None


def test_valid_jwt_with_token_row_returns_user() -> None:
    app_state: Final = _app_state(_FakeDatabase(_token_set("12345")))
    request: Final = _request_with_session_cookie(_session_jwt(app_state.config, "12345"))

    current_user: Final = get_current_user(request, app_state)
    assert current_user is not None
    assert current_user.id == "12345"
    assert current_user.login == "alice"


@pytest.mark.asyncio
async def test_revoked_twitch_tokens_render_logged_out_context(monkeypatch: pytest.MonkeyPatch) -> None:
    # The token row still exists, but Twitch rejects the tokens on validation/refresh.
    async def _refuse_tokens(app_state: AppState, user_id: str) -> NoReturn:
        raise InvalidRefreshTokenException

    monkeypatch.setattr(auth, "get_authenticated_twitch_client", _refuse_tokens)

    app_state: Final = _app_state(_FakeDatabase(_token_set("67890")))
    request: Final = _request_with_session_cookie(_session_jwt(app_state.config, "67890"))
    current_user: Final = get_current_user(request, app_state)
    assert current_user is not None

    context: Final = await get_common_context(current_user, app_state)
    assert context.current_user is None
    assert context.profile_image_url is None
    assert context.is_broadcaster is False
