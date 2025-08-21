import json
import logging
from enum import StrEnum
from typing import Final
from typing import final

from pydantic.type_adapter import TypeAdapter

from chatbot2k.config import Config


@final
class TranslationKey(StrEnum):
    COMMAND_ALREADY_EXISTS = "COMMAND_ALREADY_EXISTS"
    COMMAND_TO_UPDATE_NOT_FOUND = "COMMAND_TO_UPDATE_NOT_FOUND"
    COMMAND_TO_DELETE_NOT_FOUND = "COMMAND_TO_DELETE_NOT_FOUND"
    BUILTIN_COMMAND_CANNOT_BE_DELETED = "BUILTIN_COMMAND_CANNOT_BE_DELETED"
    COMMAND_ADDED = "COMMAND_ADDED"
    COMMAND_UPDATED = "COMMAND_UPDATED"
    COMMAND_REMOVED = "COMMAND_REMOVED"


@final
class TranslationsManager:
    def __init__(self, *, config: Config, create_if_missing: bool) -> None:
        if create_if_missing and not config.translations_file.exists():
            logging.info(f"Translations file not found, creating: {config.translations_file}")
            config.translations_file.parent.mkdir(parents=True, exist_ok=True)
            config.translations_file.write_text(
                json.dumps({}),
                encoding="utf-8",
            )
        translations_adapter: Final = TypeAdapter(type=dict[TranslationKey, str])
        self._translations: Final = translations_adapter.validate_json(
            config.translations_file.read_text(encoding="utf-8"),
        )

        # There's a bug in Pyrefly. We have to ignore the error here.
        for keys in TranslationKey:  # type: ignore[not-iterable]
            if keys not in self._translations:
                raise ValueError(f"Missing translation for key: {keys}")

    def get_translation(self, key: TranslationKey) -> str:
        return self._translations[key]
