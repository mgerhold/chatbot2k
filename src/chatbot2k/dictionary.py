import re
import time
from collections import defaultdict
from typing import Final
from typing import NamedTuple
from typing import Optional
from typing import final

from chatbot2k.database.engine import Database
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.chat_platform import ChatPlatform
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.utils.urls import remove_urls


@final
class Dictionary:
    _DEFAULT_COOLDOWN_SECONDS = 60.0
    _MAX_NUM_EXPLANATIONS_AT_ONCE = 4

    @final
    class _InternalEntry(NamedTuple):
        word: str
        pattern: re.Pattern[str]
        explanation: str

    def __init__(
        self,
        database: Database,
        *,
        cooldown: float = _DEFAULT_COOLDOWN_SECONDS,
    ) -> None:
        loaded: Final = database.get_dictionary_entries()
        self._database = database
        self._entries = [
            self._InternalEntry(
                entry.word,
                Dictionary._build_regex(entry.word),
                entry.explanation,
            )
            for entry in loaded
        ]
        self._cooldown: Final = cooldown
        self._usage_timestamps: Final[defaultdict[ChatPlatform, dict[str, float]]] = defaultdict(dict)

    def get_explanations(self, chat_message: ChatMessage) -> Optional[list[ChatResponse]]:
        chat_platform: Final = chat_message.sender_chat.platform
        # If a dictionary entry is found in a URL, we ignore it. E.g., to avoid
        # explaining "COM" in "example.com".
        stripped_text: Final = remove_urls(chat_message.text)
        matching_entries = [
            (entry.word, entry.explanation)
            for entry in self._entries
            if entry.pattern.search(stripped_text) is not None
            and not self._is_in_cooldown(
                chat_platform,
                entry.word,
            )
        ]
        if not matching_entries:
            return None
        original_number_of_matches: Final = len(matching_entries)
        is_exceeding_maximum = len(matching_entries) > Dictionary._MAX_NUM_EXPLANATIONS_AT_ONCE
        if is_exceeding_maximum:
            # Cap the number of explanations to the maximum allowed (minus one for the additional
            # info message).
            matching_entries = matching_entries[: Dictionary._MAX_NUM_EXPLANATIONS_AT_ONCE - 1]
        now: Final = time.monotonic()
        for word, _ in matching_entries:
            self._usage_timestamps[chat_platform][word] = now

        responses = [
            ChatResponse(
                text=f"{f'{word}: {explanation}'}",
                chat_message=chat_message,
            )
            for word, explanation in matching_entries
        ]
        if is_exceeding_maximum:
            responses.append(
                ChatResponse(
                    text=f"Note: Only the first {Dictionary._MAX_NUM_EXPLANATIONS_AT_ONCE - 1} explanations are shown. "
                    + "There were another "
                    + f"{original_number_of_matches - (Dictionary._MAX_NUM_EXPLANATIONS_AT_ONCE - 1)} "
                    + "explanations available.",
                    chat_message=chat_message,
                )
            )

        return responses

    def as_dict(self) -> dict[str, str]:
        return {entry.word: entry.explanation for entry in self._entries}

    def add_entry(self, *, word: str, explanation: str) -> None:
        if any(entry.word.lower() == word.lower() for entry in self._entries):
            raise AssertionError
        new_entry: Final = self._InternalEntry(
            word=word,
            pattern=Dictionary._build_regex(word),
            explanation=explanation,
        )
        self._entries.append(new_entry)
        self._database.add_dictionary_entry(word=new_entry.word, explanation=new_entry.explanation)

    def remove_entry(self, chat_platform: ChatPlatform, word: str) -> None:
        self._entries = [entry for entry in self._entries if entry.word.lower() != word.lower()]
        self._usage_timestamps[chat_platform].pop(word, None)
        self._database.remove_dictionary_entry_case_insensitive(word=word)

    def _is_in_cooldown(self, chat_platform: ChatPlatform, word: str) -> bool:
        last_used: Final = self._usage_timestamps[chat_platform].get(word)
        if last_used is None:
            return False
        return (time.monotonic() - last_used) < self._cooldown

    @staticmethod
    def _build_regex(word: str) -> re.Pattern[str]:
        escaped = re.escape(word)

        # Always match the base abbreviation case-insensitively.
        base: Final = rf"(?i:{escaped})"

        # Additionally match a plural form only if the persisted abbreviation is ALL CAPS
        # and the user wrote the ALL-CAPS abbreviation followed by a *lowercase* 's' (e.g. "ABCs").
        if word.isupper():
            plural = f"{escaped}s"  # case-sensitive
            return re.compile(rf"\b(?:{base}|{plural})\b")
        return re.compile(rf"\b{base}\b")
