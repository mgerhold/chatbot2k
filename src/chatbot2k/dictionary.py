import re
import time
from pathlib import Path
from typing import Final
from typing import NamedTuple
from typing import Optional
from typing import final

from pydantic.type_adapter import TypeAdapter

from chatbot2k.models.dictionary_entry import DictionaryEntry
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.chat_response import ChatResponse


@final
class Dictionary:
    _DEFAULT_COOLDOWN_SECONDS: Final = 60.0

    @final
    class _InternalEntry(NamedTuple):
        word: str
        pattern: re.Pattern
        explanation: str

    def __init__(
        self,
        dictionary_file: Path,
        *,
        cooldown: float = _DEFAULT_COOLDOWN_SECONDS,
    ) -> None:
        dictionary_adapter: Final = TypeAdapter(type=list[DictionaryEntry])
        loaded: Final = dictionary_adapter.validate_json(dictionary_file.read_text(encoding="utf-8"))
        self._entries: Final = [
            self._InternalEntry(
                entry.word,
                Dictionary._build_regex(entry.word),
                entry.explanation,
            )
            for entry in loaded
        ]
        self._cooldown: Final = cooldown
        self._usage_timestamps: Final[dict[str, float]] = {}

    def get_explanations(self, chat_message: ChatMessage) -> Optional[list[ChatResponse]]:
        matching_entries: Final = [
            (entry.word, entry.explanation)
            for entry in self._entries
            if entry.pattern.search(chat_message.text) is not None and not self._is_in_cooldown(entry.word)
        ]
        if not matching_entries:
            return None
        now: Final = time.monotonic()
        for word, _ in matching_entries:
            self._usage_timestamps[word] = now

        return [
            ChatResponse(
                text=f"{word}: {explanation}",
                chat_message=chat_message,
            )
            for word, explanation in matching_entries
        ]

    def as_dict(self) -> dict[str, str]:
        return {entry.word: entry.explanation for entry in self._entries}

    def _is_in_cooldown(self, word: str) -> bool:
        last_used: Optional[float] = self._usage_timestamps.get(word)
        if last_used is None:
            return False
        return (time.monotonic() - last_used) < self._cooldown

    @staticmethod
    def _build_regex(word: str) -> re.Pattern:
        pattern: Final = rf"\b{re.escape(word)}\b"
        return re.compile(pattern, re.IGNORECASE)
