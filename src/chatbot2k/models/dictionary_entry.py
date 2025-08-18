from typing import final

from pydantic.main import BaseModel


@final
class DictionaryEntry(BaseModel):
    word: str
    explanation: str
