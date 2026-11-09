#!/usr/bin/env python3
"""md_paragraphs classifies pandoc table captions as non-prose (GH-465).

    python3 test_md_paragraphs.py
"""
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import md_paragraphs  # noqa: E402

DOC = """# Lifecycle

The lifecycle square has a create and a destroy primitive for each column, and the engine reads it.

| | class | instance |
|---|---|---|
| create | define | instantiate |

Table: The lifecycle square has create and destroy primitives for each column. {#tab:lifecycle-square}

: The colon form of a caption, with its label. {#tab:colon-form}

Term
: A definition-list entry, which stays prose because it carries no table label.

The closing paragraph says one plain thing about the square and stops there.
"""


def test_table_captions_are_not_prose():
    r = md_paragraphs.parse(DOC)
    prose = [t for _s, _e, t in r.paragraphs]
    assert not any(t.startswith("Table:") for t in prose), prose
    assert not any("{#tab:" in t for t in prose), prose
    assert any(t.startswith("The lifecycle square has a create") for t in prose)
    assert any(t.startswith("The closing paragraph") for t in prose)
    assert r.coverage.get("table-caption") or "table-caption" in set(r.coverage.values()), r.coverage
    print("  table_captions_are_not_prose: ok")


def test_a_definition_list_entry_stays_prose():
    r = md_paragraphs.parse(DOC)
    prose = " ".join(t for _s, _e, t in r.paragraphs)
    assert "A definition-list entry" in prose, prose
    print("  a_definition_list_entry_stays_prose: ok")


if __name__ == "__main__":
    test_table_captions_are_not_prose()
    test_a_definition_list_entry_stays_prose()
    print("test_md_paragraphs: all assertions passed")
