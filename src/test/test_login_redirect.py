"""Tests for redirecting logged-out users to the login page when they open a page that requires a login,
and back to the requested page after logging in (without allowing open redirects)."""

from types import SimpleNamespace
from typing import Annotated
from typing import Final
from typing import Optional
from urllib.parse import parse_qs
from urllib.parse import urlsplit

import pytest
from fastapi import Depends
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.responses import Response

from chatbot2k import main
from chatbot2k.config import Environment
from chatbot2k.dependencies import NotAuthenticatedException
from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_authenticated_user
from chatbot2k.dependencies import get_common_context
from chatbot2k.dependencies import get_current_user
from chatbot2k.routes import auth
from chatbot2k.routes import login
from chatbot2k.routes.auth import _build_logged_in_response  # type: ignore[reportPrivateUsage]
from chatbot2k.routes.auth_constants import POST_LOGIN_REDIRECT_COOKIE
from chatbot2k.types.template_contexts import CommonContext
from chatbot2k.types.user_info import UserInfo
from chatbot2k.utils.redirects import get_safe_redirect_target

_BROWSER_ACCEPT_HEADER: Final = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"


@pytest.mark.parametrize(
    "target",
    [
        "/",
        "/viewer/soundboard",
        "/viewer/soundboard?tab=upload&x=%2F%2Fevil.example",
    ],
)
def test_paths_on_this_site_are_safe_redirect_targets(target: str) -> None:
    assert get_safe_redirect_target(target) == target


@pytest.mark.parametrize(
    "target",
    [
        None,
        "",
        "viewer/soundboard",
        "https://evil.example",
        "//evil.example",
        "///evil.example",
        "/\\evil.example",
        "\\\\evil.example",
        "/\t/evil.example",
        "/viewer\r\nSet-Cookie: x=y",
        "/login",
        "/login?next=/viewer/soundboard",
        "/auth/twitch/logout",
    ],
)
def test_other_targets_are_not_safe_redirect_targets(target: Optional[str]) -> None:
    assert get_safe_redirect_target(target) is None


def _make_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    async def _http_exception_handler(request: Request, exc: Exception) -> Response:
        # The real handler renders the error page, which needs the full application state.
        return PlainTextResponse("error page", status_code=401)

    monkeypatch.setattr(main, "http_exception_handler", _http_exception_handler)

    app = FastAPI()
    app.add_exception_handler(NotAuthenticatedException, main.not_authenticated_exception_handler)  # type: ignore[reportArgumentType]
    app.include_router(login.router)
    app.include_router(auth.router)

    @app.api_route("/protected", methods=["GET", "POST"])
    async def protected(  # type: ignore[reportUnusedFunction]
        current_user: Annotated[UserInfo, Depends(get_authenticated_user)],
    ) -> Response:
        return PlainTextResponse(f"Hello, {current_user.login}!")

    app.dependency_overrides[get_current_user] = lambda: None
    app.dependency_overrides[get_app_state] = lambda: SimpleNamespace(
        config=SimpleNamespace(
            twitch_chatbot_web_interface_client_id="client-id",
            twitch_redirect_uri="http://testserver/auth/twitch/callback",
            environment=Environment.DEVELOPMENT,
        )
    )
    app.dependency_overrides[get_common_context] = lambda: CommonContext(
        bot_name="TestBot",
        author_name="Tester",
        copyright_year=2026,
        current_user=None,
        profile_image_url=None,
        is_broadcaster=False,
        pending_clips_count=0,
        unread_notifications_count=0,
        total_notifications_count=0,
    )
    return TestClient(app, follow_redirects=False)


def test_logged_out_browser_is_redirected_to_login_with_requested_page(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)

    response = client.get("/protected?tab=upload", headers={"Accept": _BROWSER_ACCEPT_HEADER})

    assert response.status_code == 303
    location = urlsplit(response.headers["location"])
    assert location.path == "/login"
    assert parse_qs(location.query) == {"next": ["/protected?tab=upload"]}


@pytest.mark.parametrize(
    ("method", "accept"),
    [
        ("GET", "*/*"),  # E.g. `fetch()` calls expecting JSON.
        ("GET", "application/json"),
        ("POST", _BROWSER_ACCEPT_HEADER),  # E.g. form submissions.
    ],
)
def test_other_requests_still_get_the_error(monkeypatch: pytest.MonkeyPatch, method: str, accept: str) -> None:
    client = _make_client(monkeypatch)

    response = client.request(method, "/protected", headers={"Accept": accept})

    assert response.status_code == 401
    assert response.text == "error page"


def test_login_page_passes_redirect_target_to_twitch_login(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)

    response = client.get("/login", params={"next": "/viewer/soundboard?tab=upload"})

    assert response.status_code == 200
    assert 'href="/auth/twitch/login?next=%2Fviewer%2Fsoundboard%3Ftab%3Dupload"' in response.text


def test_login_page_ignores_unsafe_redirect_target(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)

    response = client.get("/login", params={"next": "//evil.example"})

    assert response.status_code == 200
    assert 'href="/auth/twitch/login"' in response.text
    assert "evil.example" not in response.text


def _logged_in_response_location(set_cookie_header: Optional[str]) -> str:
    """Simulates the browser sending the cookie set during login back to the OAuth callback."""
    headers: list[tuple[bytes, bytes]] = []
    if set_cookie_header is not None:
        cookie: Final = set_cookie_header.split(";", 1)[0]  # Strip attributes like `Path=...`.
        headers.append((b"cookie", cookie.encode("latin-1")))
    request: Final = Request({"type": "http", "method": "GET", "path": "/auth/twitch/callback", "headers": headers})
    response: Final = _build_logged_in_response(
        request,
        SimpleNamespace(config=SimpleNamespace(environment=Environment.DEVELOPMENT)),  # type: ignore[reportArgumentType]
        "session-jwt",
    )
    assert response.status_code == 303
    return response.headers["location"]


def _get_post_login_redirect_set_cookie_header(set_cookie_headers: list[str]) -> Optional[str]:
    return next(
        (value for value in set_cookie_headers if value.startswith(f"{POST_LOGIN_REDIRECT_COOKIE}=")),
        None,
    )


def test_user_is_redirected_back_to_requested_page_after_logging_in(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)

    login_response = client.get("/auth/twitch/login", params={"next": "/viewer/soundboard?tab=upload"})

    assert login_response.status_code == 302
    assert login_response.headers["location"].startswith("https://id.twitch.tv/oauth2/authorize")
    set_cookie_header = _get_post_login_redirect_set_cookie_header(login_response.headers.get_list("set-cookie"))
    assert set_cookie_header is not None
    assert _logged_in_response_location(set_cookie_header) == "/viewer/soundboard?tab=upload"


def test_user_is_redirected_to_main_page_after_logging_in_without_redirect_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _make_client(monkeypatch)

    login_response = client.get("/auth/twitch/login")

    # A redirect target left over from a previous, unfinished login is deleted.
    set_cookie_header = _get_post_login_redirect_set_cookie_header(login_response.headers.get_list("set-cookie"))
    assert set_cookie_header is not None
    assert "Max-Age=0" in set_cookie_header
    assert _logged_in_response_location(None) == "/"


def test_tampered_redirect_cookie_is_ignored_after_logging_in() -> None:
    assert _logged_in_response_location(f'{POST_LOGIN_REDIRECT_COOKIE}="//evil.example"') == "/"
