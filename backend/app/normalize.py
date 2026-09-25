"""Text cleanup shared by every job source, so jobs from different boards look the same."""

import hashlib
import re
from collections.abc import Iterable
from html.parser import HTMLParser

# Tags that start a new line when HTML is turned into plain text.
_BLOCK_TAGS = {
    "p", "div", "br", "ul", "ol", "li", "tr", "table", "section",
    "h1", "h2", "h3", "h4", "h5", "h6",
}
_SKIP_TAGS = {"script", "style"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)  # turns &amp; etc. into real characters
        self.parts: list[str] = []
        self._skipping = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in _SKIP_TAGS:
            self._skipping += 1
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skipping = max(0, self._skipping - 1)
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skipping:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    """Convert an HTML job description into readable plain text (bullets become "- ")."""
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    text = clean_text("".join(parser.parts))
    # "<li><p>Item</p></li>" leaves the bullet on its own line; join it back to its text.
    return re.sub(r"^-\n+(?=\S)", "- ", text, flags=re.MULTILINE)


def clean_text(text: str) -> str:
    """Normalize whitespace: one space between words, at most one blank line between paragraphs."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def content_hash(company: str, title: str, description: str) -> str:
    """Fingerprint of a posting's content, ignoring case, spacing and location.

    The same job cross-posted for several cities gets the same hash, which is how
    duplicates are detected.
    """
    normalized = " ".join(f"{company}|{title}|{description}".lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def unique_nonempty(items: Iterable[str | None]) -> list[str]:
    """Strip each item and drop blanks and repeats, keeping the original order."""
    result: list[str] = []
    for item in items:
        value = (item or "").strip()
        if value and value not in result:
            result.append(value)
    return result
