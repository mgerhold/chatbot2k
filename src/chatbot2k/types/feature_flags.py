from enum import Enum
from enum import auto
from typing import NamedTuple
from typing import final


@final
class FormattingSupport(Enum):
    NONE = auto()
    HTML = auto()
    MARKDOWN = auto()


@final
class FeatureFlags(NamedTuple):
    regular_chat: bool  # Can this chat be used for regular conversations?
    broadcasting: bool  # Is this chat capable of broadcasting messages?
    formatting_support: FormattingSupport
    can_post_live_notifications: bool
    can_trigger_soundboard: bool
    supports_giveaways: bool
