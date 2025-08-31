import logging
from pathlib import Path
from typing import Final

from chatbot2k.database.tables import Constant
from chatbot2k.models.constants import ConstantsModel


def load_constants(*, constants_file: Path, create_if_missing: bool) -> dict[str, str]:
    if create_if_missing and not constants_file.exists():
        logging.info(f"Constants file {constants_file} does not exist, creating a new one.")
        constants_file.parent.mkdir(parents=True, exist_ok=True)
        constants_file.write_text(
            ConstantsModel(constants=[]).model_dump_json(indent=2),
            encoding="utf-8",
        )
    contents: Final = constants_file.read_text()
    return {record.name: record.text for record in ConstantsModel.model_validate_json(contents).constants}


def replace_constants(text: str, constants: list[Constant]) -> str:
    for constant in constants:
        text = text.replace(f"{{{constant.name}}}", constant.text)
    return text
