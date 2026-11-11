from typing import Final
from urllib.parse import urlsplit

from chatbot2k.config import Config


def get_public_base_url(config: Config) -> str:
    """
    Returns the origin (scheme and host, without a trailing slash) under which the web
    application is publicly reachable. It is derived from the Twitch OAuth redirect URI,
    since that has to point to the public web application anyway.
    """
    parts: Final = urlsplit(config.twitch_redirect_uri)
    return f"{parts.scheme}://{parts.netloc}"
