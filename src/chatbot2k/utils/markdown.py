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


def markdown_to_text(markdown: Optional[str]) -> str:
    """
    Convert Markdown (possibly with HTML) to plain text.

    - Links become 'text (url)'.
    - Images become their alt text (plus src in parentheses if alt exists).
    - Inline/Block code kept as text.
    - Newlines only at block boundaries (no spaces inserted inside words).
    """
    if not markdown:
        return ""

    try:
        from bs4 import BeautifulSoup  # type: ignore
        from markdown_it import MarkdownIt  # type: ignore

        md = MarkdownIt("commonmark").enable("linkify").enable("strikethrough").enable("table")
        html = md.render(markdown)
        soup = BeautifulSoup(html, "html.parser")

        # Convert anchors: <a>text</a> -> "text (href)"
        for a in soup.find_all("a"):
            text = a.get_text(strip=True)
            href = (a.get("href") or "").strip()  # type: ignore[bad-argument-type]
            if href and text:
                a.replace_with(f"{text} ({href})")  # type: ignore[bad-argument-type]
            elif href:
                a.replace_with(href)  # type: ignore[bad-argument-type]
            else:
                a.replace_with(text)  # type: ignore[bad-argument-type]

        # Convert images: <img alt src> -> "alt (src)" or "[image: src]"
        for img in soup.find_all("img"):
            alt = (img.get("alt") or "").strip()  # type: ignore[missing-attribute]
            src = (img.get("src") or "").strip()  # type: ignore[missing-attribute]
            if alt and src:
                img.replace_with(f"{alt} ({src})")  # type: ignore[bad-argument-type]
            elif alt:
                img.replace_with(alt)  # type: ignore[bad-argument-type]
            elif src:
                img.replace_with(f"[image: {src}]")  # type: ignore[bad-argument-type]
            else:
                img.replace_with("[image]")  # type: ignore[bad-argument-type]

        # Turn <br> into explicit newlines
        for br in soup.find_all("br"):
            br.replace_with("\n")  # type: ignore[bad-argument-type]

        # Add newlines around *block-level* elements only
        BLOCK_TAGS = {
            "p",
            "div",
            "section",
            "article",
            "header",
            "footer",
            "main",
            "aside",
            "ul",
            "ol",
            "li",
            "dl",
            "dt",
            "dd",
            "blockquote",
            "pre",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "table",
            "thead",
            "tbody",
            "tr",
            "th",
            "td",
        }
        for tag in soup.find_all(BLOCK_TAGS):
            # newline before and after block to avoid gluing paragraphs/lists
            tag.insert_before("\n")
            assert isinstance(tag, Tag)
            tag.append("\n")

        # Extract text with *no* separator so inline nodes don't get split
        text = soup.get_text(separator="")

        return _normalize_whitespace(text)

    except Exception:
        # Fallback (unchanged): regex-based best-effort stripper
        return _markdown_regex_fallback(markdown)


def _normalize_whitespace(s: str) -> str:
    """Trim spaces per line, collapse excessive blank lines, normalize newlines."""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    # Strip trailing/leading spaces on each line
    lines = [line.strip() for line in s.split("\n")]
    # Collapse runs of blank lines to a single blank line
    out: list[str] = []
    blank = False
    for line in lines:
        if line:
            out.append(line)
            blank = False
        else:
            if not blank:
                out.append("")
            blank = True
    # Trim leading/trailing blank lines
    while out and out[0] == "":
        out.pop(0)
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out)


# Precompiled patterns for the fallback
_FENCE_RE: Final = re.compile(r"^```.*?$|^~~~.*?$", re.MULTILINE)  # fence lines
_IMAGE_RE: Final = re.compile(r"!\[([^]]*)]\(([^)]+)\)")
_LINK_RE: Final = re.compile(r"\[([^]]+)]\(([^)]+)\)")
_AUTOLINK_RE: Final = re.compile(r"<(https?://[^>\s]+)>")
_STRONG_RE: Final = re.compile(r"(\*\*|__)(.*?)\1", re.DOTALL)
_EM_RE: Final = re.compile(r"([*_])(.*?)\1", re.DOTALL)
_STRIKE_RE: Final = re.compile(r"~~(.*?)~~", re.DOTALL)
_HEADING_RE: Final = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_BLOCKQUOTE_RE: Final = re.compile(r"^\s{0,3}>\s?", re.MULTILINE)
_LIST_BULLET_RE: Final = re.compile(r"^\s{0,3}([-+*])\s+", re.MULTILINE)
_LIST_NUMBER_RE: Final = re.compile(r"^\s{0,3}\d+\.\s+", re.MULTILINE)
_HTML_TAG_RE: Final = re.compile(r"</?[^>\s/][^>]*>")  # rudimentary HTML tag stripper
_ENTITY_RE: Final = re.compile(r"&(#\d+|#x[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]+);")  # naive entity; optional


def _markdown_regex_fallback(md: str) -> str:
    """Best-effort plain-text conversion without external libs."""
    s = md

    # Remove fence marker lines (keep the code content between them)
    s = _FENCE_RE.sub("", s)

    # Inline code: keep inner text
    s = _CODE_SPAN_RE.sub(r"\1", s)

    # Images -> "alt (src)" or "[image: src]"
    def _img_repl(m: re.Match[str]) -> str:
        alt, src = m.group(1).strip(), m.group(2).strip()
        return f"{alt} ({src})" if alt else f"[image: {src}]"

    s = _IMAGE_RE.sub(_img_repl, s)

    # Links -> "text (url)"
    s = _LINK_RE.sub(lambda m: f"{m.group(1).strip()} ({m.group(2).strip()})", s)

    # Autolinks <http://...> -> http://...
    s = _AUTOLINK_RE.sub(lambda m: m.group(1), s)

    # Emphasis/strong/strike: keep inner text
    s = _STRONG_RE.sub(lambda m: m.group(2), s)
    s = _EM_RE.sub(lambda m: m.group(2), s)
    s = _STRIKE_RE.sub(lambda m: m.group(1), s)

    # Headings: drop leading hashes
    s = _HEADING_RE.sub("", s)

    # Blockquotes: drop '>'
    s = _BLOCKQUOTE_RE.sub("", s)

    # Lists: keep marker as '-' for bullets / keep numbers as-is
    s = _LIST_BULLET_RE.sub("- ", s)
    s = _LIST_NUMBER_RE.sub(lambda m: f"{m.group(0).strip()} ", s)

    # Strip rudimentary HTML tags
    s = _HTML_TAG_RE.sub("", s)

    # (Optional) decode entities minimally — or leave as-is if you rely on upstream sanitization
    s = _ENTITY_RE.sub("", s)

    return _normalize_whitespace(s)
