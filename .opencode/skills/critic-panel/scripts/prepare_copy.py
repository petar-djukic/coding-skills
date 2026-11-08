#!/usr/bin/env python3
"""Build the critics' reading copy of an article (GH-75).

Strips front matter and the REFERENCES tail, collapses figures to [figure],
marks locked spans as [[LOCKED: ... :LOCKED]] so critics can see what is
off-limits, and drops other HTML comments. Fenced blocks and inline code
spans pass through verbatim (GH-413, GH-414). Writes <stem>.critic-copy.md.
"""
import argparse
import os
import re


def _balanced(text, i, open_ch, close_ch):
    """Index just past the delimiter opened at `text[i]`, or None if unclosed.

    `i` must be the opening character. Counts depth, so a nested pair inside
    does not end the span early.
    """
    depth = 0
    while i < len(text):
        c = text[i]
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


def collapse_figures(text):
    """Replace every `![label](destination)` with `[figure]`.

    A scan rather than a regex, because both halves nest and a character class
    cannot count (GH-102). `![^\\]]*` stopped at the first `]`, so alt text
    carrying a citation — `![see [1] for detail](fig.png)` — matched nothing
    and the whole construct reached the critics as prose, markdown and URL
    included. `[^)]*` stopped at the first `)`, so a parenthesised filename
    left `.png)` behind. CommonMark resolves both by counting balance, which
    is what this does.

    An unterminated construct is left exactly as it stands. Consuming to the
    end of the document would delete the article to tidy a caption — the same
    reasoning that kept the comment strip non-greedy in GH-96, where a fix
    that could eat everything between two markers was worse than the bug.

    Not handled, deliberately: CommonMark's `<...>` destination form. It
    appears nowhere in the corpora this runs on, and adding it without a case
    to test against is speculation.
    """
    out, i = [], 0
    while True:
        j = text.find("![", i)
        if j < 0:
            out.append(text[i:])
            return "".join(out)
        label_end = _balanced(text, j + 1, "[", "]")
        if label_end is None or label_end >= len(text) or text[label_end] != "(":
            # Not a figure, or unterminated: emit `![` and keep scanning after
            # it, so a stray bracket costs two characters rather than the rest
            # of the document.
            out.append(text[i:j + 2])
            i = j + 2
            continue
        dest_end = _balanced(text, label_end, "(", ")")
        if dest_end is None:
            out.append(text[i:j + 2])
            i = j + 2
            continue
        out.append(text[i:j])
        out.append("[figure]")
        i = dest_end


_CODE_START = re.compile(
    r"<!--"
    r"|^[ ]{0,3}(?P<fence>`{3,}(?=[^`\n]*$)|~{3,})"
    r"|(?P<ticks>`+)",
    re.M,
)


def code_regions(text):
    """(start, end) of every fenced block and inline code span, in order.

    A how-to that shows a release tag as code — `<!-- release: 00.0 -->` —
    lost it to the comment strip, and every critic then reported that the
    format is never displayed (GH-413, GH-414). Code is content the reader
    sees verbatim, so none of the reading-copy rewrites may touch it.

    Comments are scanned past whole, so a backtick inside a reverse-outline
    marker never opens a span that hides the marker from the strip. An
    unclosed fence runs to the end of the document, as CommonMark has it. An
    unmatched backtick run is literal text, and its partner is sought only
    within the paragraph, so one stray backtick cannot shield the rest of the
    article from the strip.
    """
    regions, pos = [], 0
    while True:
        m = _CODE_START.search(text, pos)
        if not m:
            return regions
        if m.group(0) == "<!--":
            close = text.find("-->", m.end())
            pos = m.end() if close < 0 else close + 3
        elif m.group("fence"):
            fence = m.group("fence")
            line_end = text.find("\n", m.end())
            if line_end < 0:
                regions.append((m.start(), len(text)))
                return regions
            closing = re.compile(
                rf"^[ ]{{0,3}}{re.escape(fence[0])}{{{len(fence)},}}[ \t]*$",
                re.M).search(text, line_end + 1)
            end = len(text) if not closing else closing.end()
            regions.append((m.start(), end))
            pos = end
        else:
            ticks = m.group("ticks")
            para = re.compile(r"\n[ \t]*\n").search(text, m.end())
            limit = para.start() if para else len(text)
            closing = re.compile(rf"(?<!`){ticks}(?!`)").search(
                text, m.end(), limit)
            if closing:
                regions.append((m.start(), closing.end()))
                pos = closing.end()
            else:
                pos = m.end()


def _shield(text):
    """Swap code regions for placeholders; returns (text, originals)."""
    out, kept, pos = [], [], 0
    for start, end in code_regions(text):
        out.append(text[pos:start])
        out.append(f"\x00{len(kept)}\x00")
        kept.append(text[start:end])
        pos = end
    out.append(text[pos:])
    return "".join(out), kept


def _unshield(text, kept):
    return re.sub(r"\x00(\d+)\x00", lambda m: kept[int(m.group(1))], text)


def prepare(text):
    if text.startswith("---\n"):
        parts = text.split("\n---\n", 1)
        if len(parts) == 2:
            text = parts[1]
    text = text.split("\n## REFERENCES")[0]
    text, kept = _shield(text)
    # Locks first: once converted they carry no `<!--`, so the general strip
    # below cannot reach them. Reordering these three lines deletes the locks.
    text = re.sub(r"<!--\s*lock\s*-->", "[[LOCKED: ", text)
    text = re.sub(r"<!--\s*/lock\s*-->", " :LOCKED]]", text)
    # Non-greedy and dot-all, not `[^>]*` (GH-96). A negated class stops at the
    # first `>`, so a reverse-outline marker carrying `-> n` never matched at
    # all and reached the critics whole — 19 of them on one 5,500-word article,
    # read as if they were prose. Greedy `.*` would be worse than the bug: it
    # would swallow every line between the first comment and the last.
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = collapse_figures(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return _unshield(text, kept).strip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article")
    ap.add_argument("--out")
    a = ap.parse_args()
    with open(a.article, encoding="utf-8") as f:
        out = prepare(f.read())
    path = a.out or os.path.splitext(a.article)[0] + ".critic-copy.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"{path}  ({len(out.split())} words, "
          f"{out.count('[[LOCKED:')} locked spans)")


if __name__ == "__main__":
    main()
