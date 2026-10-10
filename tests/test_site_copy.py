"""The demo page speaks to strangers: internal names stay out of its labels, and every attack has a plain one.

Only the page's own HTML and JS are checked. The recorded data in replay.js keeps its internal titles.
"""

from __future__ import annotations

import json
import re
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
