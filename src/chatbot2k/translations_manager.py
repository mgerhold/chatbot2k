from typing import Final
from typing import final

from chatbot2k.database.engine import Database
from chatbot2k.translation_key import TranslationKey


@final
class TranslationsManager:
    def __init__(self, database: Database) -> None:
        self._translations: Final = database.get_translations()

        for key in TranslationKey:
            if key not in (translation.key for translation in self._translations):
                raise ValueError(f"Missing translation for key: {key}")

    def get_translation(self, key: TranslationKey) -> str:
        return next(translation.value for translation in self._translations if translation.key == key)
