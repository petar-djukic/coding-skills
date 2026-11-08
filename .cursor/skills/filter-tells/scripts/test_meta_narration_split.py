#!/usr/bin/env python3
"""The loose meta-narration patterns report under their own category (GH-408).

    python3 test_meta_narration_split.py

Measured on autogenic-systems' eval corpus, the combined meta-narration
category fired on 10 of 27 human samples against 9 of 49 AI ones. The
self-description and brief-echo phrases carried that; split out as
meta-narration-loose, the tight category fired on 2/27 against 3/49. These
tests pin which bucket each kind of phrase lands in, and that the driver
labels the loose bucket as lower priority.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
SCRIPT = os.path.join(HERE, "detect-lexical.sh")
sys.path.insert(0, HERE)
import drive  # noqa: E402


def _categories(text):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(text + "\n")
        path = f.name
    try:
        r = subprocess.run(["bash", SCRIPT, path, "--json"],
                           capture_output=True, text=True)
        data = json.loads(r.stdout)
    finally:
        os.unlink(path)
    items = data.get("issues", []) if isinstance(data, dict) else data
    return {(h["category"], h["pattern"]) for h in items if isinstance(h, dict)}


def _cats(text):
    return {c for c, _ in _categories(text)}


def test_tight_patterns_stay_meta_narration():
    for text in ("The definition is stated here and cited by every section of it.",
                 "In the sections that follow, the protocol gets its framing.",
                 "The appendix shows what that takes in practice."):
        cats = _cats(text)
        assert "meta-narration" in cats and "meta-narration-loose" not in cats, (text, cats)
    print("  tight_patterns_stay_meta_narration: ok")


def test_self_description_is_loose():
    cats = _cats("This paper presents a distributed scheduling algorithm for mesh networks.")
    assert "meta-narration-loose" in cats and "meta-narration" not in cats, cats
    print("  self_description_is_loose: ok")


def test_brief_echo_phrases_are_loose():
    for phrase in ("The cache is small by design and refills on demand.",
                   "We left the field empty on purpose so the parser fails fast.",
                   "A reader who skips the appendix loses nothing.",
                   "The standard does not specify a transport."):
        cats = _cats(phrase)
        assert "meta-narration-loose" in cats and "meta-narration" not in cats, (phrase, cats)
    print("  brief_echo_phrases_are_loose: ok")


def test_driver_labels_the_loose_bucket():
    cands = [{"category": "meta-narration", "line": 3, "text": "stated here and cited"},
             {"category": "meta-narration-loose", "line": 9, "text": "This paper presents"}]
    out = drive._meta_narration_hits(cands)
    assert out.index("stated here") < out.index("Lower priority") < out.index("This paper")
    only_tight = drive._meta_narration_hits(cands[:1])
    assert "Lower priority" not in only_tight
    assert drive._meta_narration_hits([]) == "(none)"
    print("  driver_labels_the_loose_bucket: ok")


def main():
    test_tight_patterns_stay_meta_narration()
    test_self_description_is_loose()
    test_brief_echo_phrases_are_loose()
    test_driver_labels_the_loose_bucket()
    print("test_meta_narration_split: all assertions passed")


if __name__ == "__main__":
    main()
