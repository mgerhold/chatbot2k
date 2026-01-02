from chatbot2k.database.tables import Constant


def replace_constants(text: str, constants: list[Constant]) -> str:
    for constant in constants:
        text = text.replace(f"{{{constant.name}}}", constant.text)
    return text
