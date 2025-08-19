import logging
from typing import Final

from chatbot2k.config import CONFIG
from chatbot2k.models.constants import ConstantsModel


def _load_constants(*, create_if_missing: bool) -> dict[str, str]:
    if create_if_missing and not CONFIG.constants_file.exists():
        logging.info(f"Constants file {CONFIG.constants_file} does not exist, creating a new one.")
        CONFIG.constants_file.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.constants_file.write_text(
            ConstantsModel(constants=[]).model_dump_json(indent=2),
            encoding="utf-8",
        )
    contents: Final = CONFIG.constants_file.read_text()
    return {record.name: record.text for record in ConstantsModel.model_validate_json(contents).constants}


CONSTANTS = _load_constants(create_if_missing=True)


def replace_constants(text: str) -> str:
    for name, value in CONSTANTS.items():
        text = text.replace(f"{{{name}}}", value)
    return text
