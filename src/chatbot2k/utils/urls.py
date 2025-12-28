import re
from typing import Final

from urlextract import URLExtract  # type: ignore[reportMissingTypeStubs]


def remove_urls(text: str) -> str:
    """
    Removes all URLs from the given text.
    """
    extractor: Final = URLExtract()
    urls: Final = extractor.find_urls(text, with_schema_only=False)

    for url in sorted(set(urls), key=len, reverse=True):
        if not isinstance(url, str):
            raise TypeError(f"Expected string URL, got {type(url)}")
        pattern = re.escape(url) + r"(?=[\s\]\[(){}<>\"'`]|$|[.,!?;:])"
        text = re.sub(
            pattern,
            "",
            text,
        )

    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()
