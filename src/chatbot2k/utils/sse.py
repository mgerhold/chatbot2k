from pydantic import BaseModel


def sse_encode(data: BaseModel) -> str:
    parts: list[str] = ["event: message"]
    # `splitlines` to be safe with multi-line payloads.
    for line in data.model_dump_json().splitlines() or [""]:
        parts.append(f"data: {line}")
    parts.append("")  # Blank line terminator.
    parts.append("")  # Blank line terminator.
    return "\r\n".join(parts)
