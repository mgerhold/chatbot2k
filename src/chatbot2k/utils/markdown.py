import re
from typing import Final
from typing import Optional

import bleach
from bs4 import BeautifulSoup
from bs4.element import Tag
from markdown_it import MarkdownIt
from markupsafe import Markup

_MARKDOWN = MarkdownIt("commonmark").enable("strikethrough").enable("linkify")

_ALLOWED_HTML_TAGS = {
    "b",
    "strong",
    "i",
    "em",
    "u",
    "s",
    "code",
    "pre",
    "kbd",
    "p",
    "br",
    "ul",
    "ol",
    "li",
    "blockquote",
    "a",
}

_ALLOWED_HTML_ATTRIBUTES = {
    "a": ["href", "title", "rel"],
}
_ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def _target_blank_and_safe_rels(attrs, new=False):
    """
    Linkify callback: force external links to open in a new tab and add safe rels.
    Runs for both newly-created links and existing <a> tags (when skip_tags=()).
    """
    href = attrs.get("href", "")
    # Only affect absolute http(s) links; skip mailto: and relative links
    if href.startswith("http://") or href.startswith("https://"):
        attrs["target"] = "_blank"
        existing = set((attrs.get("rel") or "").split())
        required = {"noopener", "noreferrer", "nofollow"}
        attrs["rel"] = " ".join(sorted(existing | required))
    return attrs


_cleaner = bleach.Cleaner(
    tags=_ALLOWED_HTML_TAGS,
    attributes=_ALLOWED_HTML_ATTRIBUTES,
    protocols=_ALLOWED_PROTOCOLS,
    strip=True,
    strip_comments=True,
)


def _force_new_tab(html: str) -> str:
    """Ensure external links open in a new tab and have safe rel."""
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]  # type: ignore[unsupported-operation]
        assert isinstance(href, str)
        # Only touch absolute http(s) (adjust if you want mailto: too)
        if href.startswith(("http://", "https://", "//")):
            a["target"] = "_blank"  # type: ignore[unsupported-operation]
            assert isinstance(a, Tag)
            rel = a.get("rel", "")
            # BeautifulSoup may give rel as list or string; normalize to set
            if isinstance(rel, str):
                rel = rel.split()
            assert rel is not None
            a["rel"] = " ".join(sorted(set(rel) | {"noopener", "noreferrer", "nofollow"}))
    return str(soup)


def markdown_to_sanitized_html(text: Optional[str]) -> Markup:
    """Markdown → HTML → sanitize → linkify bare URLs → add target+rel → Markup."""
    if not text:
        return Markup("")
    html = _MARKDOWN.render(text)
    cleaned = _cleaner.clean(html)
    # Optional: also convert any bare URLs that Markdown didn't catch
    linkified = bleach.linkify(cleaned)  # no callbacks needed now
    assert isinstance(linkified, str)
    final = _force_new_tab(linkified)
    return Markup(final)


# Match inline code (`...`) or fenced blocks (```...```)
_CODE_SPAN_RE: Final = re.compile(r"(```[\s\S]*?```|`[^`]*`)")
# Match a single-level {...} (no nested braces)
_BRACED_RE: Final = re.compile(r"\{[^{}\n]*}")


def quote_braced_with_backticks(
    text: Optional[str],
    *,
    only_these: Optional[set[str]] = None,
) -> str:
    """
    Wrap single-level {...} with backticks, skipping code spans/blocks.

    If only_builtins=True, only wrap when the inner text equals a Builtin
    enum member name (e.g., {CURRENT_DATE}, {CURRENT_TIME}).
    """
    if not text:
        return ""

    def _should_wrap(braced: str) -> bool:
        if only_these is None:
            return True
        inner = braced[1:-1].strip()  # remove { and }, allow spaces around
        return inner in only_these  # type: ignore[arg-type]

    def _wrap_segment(segment: str) -> str:
        def repl(m: re.Match[str]) -> str:
            s = m.group(0)
            return f"`{s}`" if _should_wrap(s) else s

        return _BRACED_RE.sub(repl, segment)

    parts: list[str] = []
    last = 0
    for m in _CODE_SPAN_RE.finditer(text):
        parts.append(_wrap_segment(text[last : m.start()]))
        parts.append(m.group(0))  # keep code span untouched
        last = m.end()
    parts.append(_wrap_segment(text[last:]))

    return "".join(parts)
