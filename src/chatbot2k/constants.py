from typing import Final

from chatbot2k.config import CONFIG
from chatbot2k.models.constants import ConstantsModel


def _load_constants() -> dict[str, str]:
    contents: Final = CONFIG.constants_file.read_text()
    return {record.name: record.text for record in ConstantsModel.model_validate_json(contents).constants}


CONSTANTS = _load_constants()


def replace_constants(text: str) -> str:
    for name, value in CONSTANTS.items():
        text = text.replace(f"{{{name}}}", value)
    return text
