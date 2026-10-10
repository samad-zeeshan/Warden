"""The demo page speaks to strangers: internal names stay out of its labels, and every attack has a plain one.

Only the page's own HTML and JS are checked. The recorded data in replay.js keeps its internal titles.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

SITE = Path(__file__).resolve().parents[1] / "site"
PAGE_FILES = [SITE / "index.html", SITE / "app.js", SITE / "data" / "labels.js"]

# Phrases a reader outside the project cannot place. Each was on the page once as a label.
BANNED = [
    "A2M",
    "Split:",
    "writes an attacker could still make",
    "in-process transport",
    "python -m eval.record_demo",
    "recorded_with",
    "feature flag",
    "freeze window",
    "prompt injection",
    "prompt-injection",
    "SHA-256 chained",
    "Chain verifies",
    "does not verify",
    "tool description",
    "Attacker: ",
    "Approved on its own",
    "in version 1",
]
MAX_LABEL_WORDS = 10


def _labels() -> dict[str, str]:
    text = (SITE / "data" / "labels.js").read_text(encoding="utf-8")
    body = text[text.index("= {") + 2 : text.rindex("}") + 1]
    return json.loads(body)


def test_no_banned_phrase_on_the_page():
    for path in PAGE_FILES:
        text = path.read_text(encoding="utf-8")
        for phrase in BANNED:
            assert phrase.lower() not in text.lower(), f"{phrase!r} in {path.name}"


def test_every_recorded_attack_has_a_short_plain_label():
    replay = json.loads((SITE / "data" / "replay.json").read_text(encoding="utf-8"))
    labels = _labels()
    assert set(labels) == {a["id"] for a in replay["attacks"]}
    for case_id, label in labels.items():
        assert len(label.split()) <= MAX_LABEL_WORDS, case_id
        # A label that only repeats the id is not a label.
        assert case_id not in label


def test_recorder_selectors_exist():
    html = (SITE / "index.html").read_text(encoding="utf-8")
    assert re.findall(r'data-demo="([^"]+)"', html) == ["safe", "dangerous", "attack", "tamper"]


# Plain-language rules for the README and every string the page shows. Filler words and long
# sentences slip back in one edit at a time, so they are checked on every run.
FILLER = ["comprehensive", "robust", "seamless", "cutting-edge", "state-of-the-art", "powerful",
          "leverage", "utilize", "ensure", "delve", "showcase", "crucial", "various", "numerous",
          "simply", "just", "really", "basically", "actually"]
MAX_SENTENCE_WORDS = 25


class _Text(HTMLParser):
    """Collect the text a visitor sees, plus the attributes that show up as text."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        a = dict(attrs)
        for key in ("alt", "aria-label", "title", "label"):
            if a.get(key):
                self.parts.append(a[key])
        if tag == "meta" and a.get("name") == "description" or a.get("property", "").startswith("og:"):
            self.parts.append(a.get("content", ""))

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.parts.append(data.strip())


def _page_strings() -> list[str]:
    parser = _Text()
    parser.feed((SITE / "index.html").read_text(encoding="utf-8"))
    app = (SITE / "app.js").read_text(encoding="utf-8")
    # Only literals with a space are page text. The rest are selectors, keys and class names.
    literals = [s for s in re.findall(r'"((?:[^"\\]|\\.)*)"', app) if " " in s.strip()]
    return parser.parts + literals + list(_labels().values())


def _readme_prose() -> list[str]:
    text = (SITE.parent / "README.md").read_text(encoding="utf-8")
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    # Table rows are generated numbers. Each list item counts as its own sentence.
    lines = [("\n" + ln if ln.startswith("- ") else ln) for ln in text.splitlines()
             if not ln.lstrip().startswith("|")]
    prose = "\n".join(lines)
    prose = re.sub(r"`[^`]*`", "", prose)
    prose = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", prose)
    return [p for p in re.split(r"\n\s*\n", prose) if p.strip()]


def _sentences(block: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", " ".join(block.split())) if s]


def _all_text() -> list[tuple[str, str]]:
    return [("README", b) for b in _readme_prose()] + [("page", s) for s in _page_strings()]


def test_no_filler_words():
    for where, text in _all_text():
        for word in FILLER:
            assert not re.search(rf"\b{re.escape(word)}\b", text, re.I), f"{word!r} in {where}: {text}"


def test_sentences_stay_short():
    for where, text in _all_text():
        for sentence in _sentences(text):
            assert len(sentence.split()) <= MAX_SENTENCE_WORDS, f"{where}: {sentence}"


def test_no_em_dash_or_semicolon_in_prose():
    for where, text in _all_text():
        assert "—" not in text and ";" not in text, f"{where}: {text}"
