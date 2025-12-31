from typing import Final
from typing import NamedTuple
from typing import final


@final
class LiveNotificationTextTemplate:
    def __init__(self, template_text: str) -> None:
        self._template_text: Final = template_text

    def render(self, *, broadcaster: str) -> str:
        replacements: Final = {
            "{broadcaster}": broadcaster,
        }
        rendered_text = self._template_text
        for placeholder, value in replacements.items():
            rendered_text = rendered_text.replace(placeholder, value)
        return rendered_text


@final
class LiveNotification(NamedTuple):
    broadcaster: str
    target_channel: str
    text_template: LiveNotificationTextTemplate

    def render_text(self) -> str:
        return self.text_template.render(broadcaster=self.broadcaster)
