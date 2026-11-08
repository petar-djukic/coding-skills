#!/usr/bin/env python3
"""critic-apply — rule-based application of a converged critic sheet
(GH-206).

Consumes a converge.py sheet and an article, applies the operator policy
(2026-09-01) mechanically, and reports applied/kept/declined-by-rule
counts for the generation: block. The rules, as code:

  accept    every convergent target (2+ distinct critics on one passage)
  accept    a single-critic CUT whose paragraph the reverse-outline sheet
            ranked cheap (cross-instrument agreement counts as
            convergence for deletions)
  skip      split panels — a proposal beside a dissent (KEEP / NO CHANGE)
            is not convergence
  decline   targets inside a protected or locked span, with cause; the
            constitution outranks the panel
  prefer    the omission when remedies conflict inside a convergence —
            a deletion authors no prose

Application mechanics, learned the hard way: rst markers are stripped
before the model call and reattached after (their digits fail the number
gate — measured); each rewrite target gets a narrow one-sentence
instruction through the rewrite transport, never persona prose spliced
in; every candidate passes a mechanical gate (number multiset, citation
multiset, em-dash/colon budget, 0.5–1.35 size band) or the original is
kept; deletions apply directly with mechanical punctuation
normalization. Every accepted target in a paragraph applies, in document
order, each to the text the previous one left (GH-430); paragraphs run
concurrently (--jobs).
"""

import argparse
import difflib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
SHARED = os.path.normpath(os.path.join(HERE, "..", "..", "..", "scripts"))
MATCH_VOICE = os.path.normpath(os.path.join(HERE, "..", "..", "match-voice",
                                            "scripts"))
sys.path.insert(0, SHARED)
import md_paragraphs  # noqa: E402

THRESHOLD = 0.8
RST = re.compile(r"<!--\s*rst:.*?-->\s*", re.S)
DISSENT = re.compile(r"^\s*(KEEP|NO CHANGE|LEAVE|AS IS)\b", re.I)
CUT = re.compile(r"^\s*CUT\b")
NUM = re.compile(r"\d[\d,\.]*")
CITE = re.compile(r"\[@[^\]\s]+\]|\[\d{1,3}\]")


def norm(s):
    return " ".join(s.lower().split())


def parse_sheet(text):
    """Convergent and single-critic targets out of a converge.py sheet."""
    targets = []
    m = re.search(r"^## Convergent[^\n]*\n(.*?)(?=^## |\Z)", text,
                  re.M | re.S)
    if m:
        for block in re.split(r"^### ", m.group(1), flags=re.M)[1:]:
            qm = re.match(r'"(.*?)"\s*\n', block, re.S)
            if not qm:
                continue
            entries = []
            for c, b, w in re.findall(
                    r"^- \*\*([^:*]+):\*\*\s*(.*?)(?:\s+—\s+\*(.*?)\*)?\s*$",
                    block, re.M):
                entries.append({"critic": c.strip(), "body": b.strip(),
                                "why": (w or "").strip()})
            if entries:
                targets.append({"quote": qm.group(1), "convergent": True,
                                "entries": entries})
    m = re.search(r"^## Single-critic[^\n]*\n(.*?)(?=^## |\Z)", text,
                  re.M | re.S)
    if m:
        critic = None
        for line in m.group(1).splitlines():
            hm = re.match(r"^### (\S+)", line)
            if hm:
                critic = hm.group(1)
                continue
            im = re.match(
                r'^\d+\.\s+"(.*)"\s+→\s+(.*?)(?:\s+—\s+\*(.*)\*)?\s*$', line)
            if im and critic:
                targets.append({
                    "quote": im.group(1), "convergent": False,
                    "entries": [{"critic": critic,
                                 "body": im.group(2).strip(),
                                 "why": (im.group(3) or "").strip()}]})
    return targets


def strip_rst(text):
    """(clean_text, markers) — markers reattach verbatim, in order, at the
    paragraph head after a rewrite. Their digits otherwise fail the
    number gate (measured on the first automated run)."""
    markers = RST.findall(text)
    return RST.sub("", text).strip(), [m.strip() for m in markers]


def find_paragraph(paras, quote):
    """1-based prose paragraph containing the quote, else None."""
    q = norm(quote)
    for n, (s, e, txt) in enumerate(paras, 1):
        t = norm(strip_rst(txt)[0])
        if q in t:
            return n
    best, best_n = 0.0, None
    for n, (s, e, txt) in enumerate(paras, 1):
        r = difflib.SequenceMatcher(
            None, q, norm(strip_rst(txt)[0]), autojunk=False).ratio()
        if r > best:
            best, best_n = r, n
    return best_n if best >= 0.6 else None


def _flexible_pattern(quote):
    return r"\s+".join(re.escape(w) for w in quote.split())


def normalize_punct(text):
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" +([,.;:!?])", r"\1", text)
    text = re.sub(r"([,;:]) *([,.;:])", r"\2", text)
    return text.strip()


def delete_quote(par_text, quote):
    """Remove the quoted sentence from the paragraph; '' if nothing is
    left. Whitespace-flexible so a reflowed paragraph still matches."""
    clean, markers = strip_rst(par_text)
    new = re.sub(_flexible_pattern(quote), " ", clean, count=1)
    if norm(new) == norm(clean):
        return None
    new = normalize_punct(new)
    if not new:
        return ""
    return "\n".join(markers + [new]) if markers else new


WORD = re.compile(r"[\w'’-]+")


def deletion_only(quote, body):
    """True when body is quote with words removed and none added: its
    words, case aside, are a strict subsequence of the quote's. Only
    punctuation and capitalization may differ, so applying it authors
    no prose."""
    if CUT.match(body) or DISSENT.match(body):
        return False
    q = [w.lower() for w in WORD.findall(quote)]
    b = [w.lower() for w in WORD.findall(body)]
    if not b or len(b) >= len(q):
        return False
    it = iter(q)
    return all(w in it for w in b)


def apply_deletion(par_text, quote, body):
    """Swap the quoted span for its trimmed form; None if not found."""
    clean, markers = strip_rst(par_text)
    new = re.sub(_flexible_pattern(quote), lambda _m: body, clean, count=1)
    if norm(new) == norm(clean):
        return None
    new = normalize_punct(new)
    return "\n".join(markers + [new]) if markers else new


# Words a critic uses about prose and a paragraph about its subject almost
# never does (GH-440). In the S2 run a candidate replaced a claim with "The
# gloss tells a modelling reader who TM Forum is...", another with "The
# consequence moves from a participle tail...", and both passed every gate.
# A term counts only when the candidate introduces it: a paragraph that
# already says "reader" may keep saying it.
_EDITORIAL = re.compile(
    r"\b(gloss(?:es|ed)?|participles?|participial|nominali[sz]ations?|"
    r"finite (?:verb|clause)s?|subordinate clauses?|clauses?|"
    r"(?:this|the|that) (?:sentence|paragraph|passage|rewrite|edit|critic)s?|"
    r"(?:a|the|modelling|modeling|cold) readers?|"
    r"consequence moves|moves from a|warrant tails?|the original (?:sentence|claim|wording))\b",
    re.I)
ECHO_RUN = 6


def _words_lower(text):
    return [w.lower() for w in WORD.findall(text)]


def rationale_leak(orig_clean, cand, instruction=""):
    """Why `cand` reads as the edit's reasoning rather than the subject, or
    "" when it does not. Two signals: critic vocabulary the original did not
    use, and a run of ECHO_RUN or more words copied from the instruction
    that the original did not already contain."""
    new_terms = sorted({m.group(0).lower() for m in _EDITORIAL.finditer(cand)}
                       - {m.group(0).lower() for m in _EDITORIAL.finditer(orig_clean)})
    if new_terms:
        return f"editorial rationale in candidate ({', '.join(new_terms)})"
    if instruction:
        iw, cw = _words_lower(instruction), _words_lower(cand)
        orig_text = " ".join(_words_lower(orig_clean))
        cand_text = " ".join(cw)
        for i in range(len(iw) - ECHO_RUN + 1):
            run = " ".join(iw[i:i + ECHO_RUN])
            if run in cand_text and run not in orig_text:
                return f"candidate echoes the instruction (\"{run}\")"
    return ""


def gate(orig_clean, cand, instruction=""):
    """Mechanical gate. Returns (ok, reason)."""
    leak = rationale_leak(orig_clean, cand, instruction)
    if leak:
        return False, leak
    if sorted(NUM.findall(CITE.sub(" ", cand))) != \
            sorted(NUM.findall(CITE.sub(" ", orig_clean))):
        return False, "number multiset changed"
    if sorted(CITE.findall(cand)) != sorted(CITE.findall(orig_clean)):
        return False, "citation multiset changed"
    for ch, name in (("—", "em-dash"), (":", "colon")):
        if cand.count(ch) > orig_clean.count(ch):
            return False, f"{name} budget exceeded"
    ow, cw = len(orig_clean.split()), len(cand.split())
    if not ow or not (0.5 <= cw / ow <= 1.35):
        return False, f"size band ({cw}/{ow} words)"
    return True, ""


def build_prompt(par_clean, quote, instruction):
    return ("Rewrite the paragraph below, changing ONLY the quoted "
            "sentence, per the instruction. Keep every citation, number, "
            "and quoted phrase exactly. Return only the rewritten "
            "paragraph, no preamble.\n"
            f"Instruction: {instruction}\n"
            f'Sentence to change: "{quote}"\n'
            f"Paragraph:\n{par_clean}")


def _decide(paras, t, protected, cheap):
    """The rule half of the policy for one target, no model involved.

    Returns (record, plan). plan is None when the rules settle the target;
    otherwise (paragraph number, kind, data) with kind cut, trim or rewrite."""
    rec = {"quote": t["quote"][:80],
           "critics": sorted({e["critic"] for e in t["entries"]})}
    n = find_paragraph(paras, t["quote"])
    rec["paragraph"] = n
    bodies = [e["body"] for e in t["entries"]]
    is_cut = any(CUT.match(b) for b in bodies)

    if t["convergent"] and any(DISSENT.match(b) for b in bodies) \
            and not all(DISSENT.match(b) for b in bodies):
        rec["status"] = "skipped-split-panel"
        return rec, None
    if not t["convergent"] and not (is_cut and n in cheap):
        rec["status"] = "skipped-not-convergent"
        return rec, None
    if not t["convergent"]:
        rec["cross_instrument"] = "reverse-outline-cheap"
    if n is None:
        rec["status"] = "kept-target-not-found"
        return rec, None
    par_text = paras[n - 1][2]
    hit = next((p for p in protected
                if norm(p) and norm(p) in norm(par_text)), None)
    if hit:
        rec["status"] = "declined-constitution"
        rec["cause"] = f"protected span: {hit[:60]}"
        return rec, None
    if is_cut:
        return rec, (n, "cut", None)
    trims = [b for b in bodies if deletion_only(t["quote"], b)]
    if trims and len(trims) == len(bodies):
        return rec, (n, "trim", max(trims, key=lambda b: len(WORD.findall(b))))
    # A remedy conflict without a CUT is still one shared finding — the
    # instruction is the why.
    return rec, (n, "rewrite", next((e["why"] for e in t["entries"] if e["why"]),
                                    t["entries"][0]["body"]))


def _content_words(text):
    return {w for w in _words_lower(text) if len(w) > 3}


def _dependent_deletions(steps):
    """Deletions that lean on a rewrite the chain did not apply (GH-441).

    The sheet carries no finding ids, so the link is read off the text: a
    deletion depends on a kept rewrite when most of what it removes appears
    in that rewrite's proposed replacement, i.e. the critics cut the
    sentence because the rewrite was going to carry its content. In the S2
    run the gate kept the rewrite that moved P3's working definition, the
    cuts of the definition went in anyway, and "This property" was left
    pointing at nothing. Returns {id(rec): reason}."""
    kept_rewrites = [(t, rec) for t, rec, kind, _d in steps
                     if kind == "rewrite" and not rec.get("status", "").startswith("applied")]
    out = {}
    if not kept_rewrites:
        return out
    for t, rec, kind, data in steps:
        if kind not in ("cut", "trim") or rec.get("status") != "applied-deletion":
            continue
        removed = _content_words(t["quote"])
        if kind == "trim":
            removed -= _content_words(data or "")
        if not removed:
            continue
        for rt, rrec in kept_rewrites:
            carried = set().union(*(_content_words(e["body"]) for e in rt["entries"]))
            if len(removed & carried) * 2 >= len(removed):
                out[id(rec)] = (f"paired rewrite kept ({rrec.get('status')}"
                                f"{': ' + rrec['cause'] if rrec.get('cause') else ''}): "
                                f"{rt['quote'][:60]}")
                break
    return out


def _apply_chain(par_text, steps, generate):
    """The chain, re-run without any deletion whose paired rewrite was kept,
    until no such deletion remains. Model answers are cached by prompt, so a
    re-run re-asks only where the paragraph text it shows has changed."""
    cache = {}

    def cached(prompt):
        if prompt not in cache:
            cache[prompt] = generate(prompt)
        return cache[prompt]

    gen = cached if generate is not None else None
    held = {}
    for _ in range(len(steps) + 1):
        live = [st for st in steps if id(st[1]) not in held]
        for _t, rec, _k, _d in live:
            rec.pop("status", None)
            rec.pop("cause", None)
        final = _run_chain(par_text, live, gen)
        new = _dependent_deletions(live)
        if not new:
            break
        held.update(new)
    for _t, rec, _k, _d in steps:
        if id(rec) in held:
            rec["status"] = "kept-gate"
            rec["cause"] = held[id(rec)]
    return final


def _run_chain(par_text, steps, generate):
    """Apply every planned target to one paragraph, in document order.

    Each step works on the text the previous step left (GH-430: one edit
    per paragraph per pass left 22 of 23 convergent targets unapplied on
    the Loom introduction, and the same ones came back every round). Each
    step is gated against the state before it, so number, citation, dash
    and colon invariants hold along the chain by transitivity. Size does
    not compose that way — two 1.3x rewrites make 1.7x — so a chain with
    no cut is checked against the original paragraph at the end and rolled
    back to its longest prefix that still fits the band.
    Returns the final paragraph text (None when nothing changed)."""
    cur, changed = par_text, False
    states = []          # (text after step, rec) for each applied step
    for t, rec, kind, data in steps:
        if cur == "":
            rec["status"] = "kept-paragraph-deleted"
            continue
        gone = "kept-quote-gone-after-edit" if changed else "kept-quote-not-in-paragraph"
        if kind == "cut":
            new = delete_quote(cur, t["quote"])
            if new is None:
                rec["status"] = gone
                continue
            rec["status"] = "applied-deletion"
        elif kind == "trim":
            new = apply_deletion(cur, t["quote"], data)
            if new is None:
                rec["status"] = gone
                continue
            clean, cand = strip_rst(cur)[0], strip_rst(new)[0]
            if sorted(NUM.findall(CITE.sub(" ", cand))) != \
                    sorted(NUM.findall(CITE.sub(" ", clean))) or \
                    sorted(CITE.findall(cand)) != sorted(CITE.findall(clean)):
                rec["status"] = "kept-gate"
                rec["cause"] = "deletion removed a number or citation"
                continue
            rec["status"] = "applied-deletion"
        else:
            if generate is None:
                rec["status"] = "kept-no-model"
                continue
            clean, markers = strip_rst(cur)
            if changed and norm(t["quote"]) not in norm(clean):
                rec["status"] = gone
                continue
            try:
                cand = generate(build_prompt(clean, t["quote"], data))
            except Exception as e:  # transport errors keep the original
                rec["status"] = "kept-rewrite-error"
                rec["cause"] = str(e)[:120]
                continue
            cand = (cand or "").strip().strip("`").strip()
            ok, why_not = gate(clean, cand, data)
            if not ok:
                rec["status"] = "kept-gate"
                rec["cause"] = why_not
                continue
            new = "\n".join(markers + [cand]) if markers else cand
            rec["status"] = "applied-rewrite"
        cur, changed = new, True
        states.append((cur, rec))

    if not changed:
        return None
    if cur and not any(r["status"] == "applied-deletion" and k == "cut"
                       for (_t, r, k, _d) in steps):
        orig = strip_rst(par_text)[0]
        while states:
            ok, why_not = gate(orig, strip_rst(states[-1][0])[0])
            if ok:
                break
            _text, rec = states.pop()
            rec["status"] = "kept-chain-drift"
            rec["cause"] = f"chain vs original: {why_not}"
        if not states:
            return None
        cur = states[-1][0]
    return cur


def decide_and_apply(article_text, targets, generate=None,
                     protected=(), cheap=frozenset(), jobs=4):
    """The whole policy. Returns (new_text, records).

    Rules settle each target first, with no model call. The surviving
    targets are grouped by paragraph and each paragraph's chain runs on its
    own thread (`jobs`; 1 is sequential). Paragraphs are independent, so
    the output does not depend on `jobs`."""
    parsed = md_paragraphs.parse(article_text)
    paras = parsed.paragraphs
    records, chains = [], {}
    for t in targets:
        rec, plan = _decide(paras, t, protected, cheap)
        records.append(rec)
        if plan:
            n, kind, data = plan
            chains.setdefault(n, []).append((t, rec, kind, data))

    def run(n):
        return n, _apply_chain(paras[n - 1][2], chains[n], generate)

    edits = {}
    if jobs and jobs > 1 and len(chains) > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            results = list(pool.map(run, sorted(chains)))
    else:
        results = [run(n) for n in sorted(chains)]
    for n, final in results:
        if final is not None:
            edits[n] = final

    # Splice bottom-up so earlier line ranges stay valid.
    lines = article_text.split("\n")
    for n in sorted(edits, reverse=True):
        s, e, _txt = paras[n - 1]
        if edits[n] == "":
            del lines[s - 1:e]
            # a deleted paragraph takes its rst marker line with it
            i = s - 2
            while i >= 0 and not lines[i].strip():
                i -= 1
            if i >= 0 and RST.match(lines[i].strip()):
                del lines[i]
        else:
            lines[s - 1:e] = edits[n].split("\n")
    return "\n".join(lines), records


def counts(records):
    c = {}
    for r in records:
        c[r["status"]] = c.get(r["status"], 0) + 1
    return {"applied": sum(v for k, v in c.items() if k.startswith("applied")),
            "kept": sum(v for k, v in c.items() if k.startswith("kept")),
            "declined_by_rule": sum(v for k, v in c.items()
                                    if k.startswith(("declined", "skipped"))),
            "by_status": c}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--article", required=True)
    ap.add_argument("--sheet", required=True,
                    help="converge.py sheet (<stem>.critic-sheet.md)")
    ap.add_argument("--out", help="default: <article stem>.applied.md")
    ap.add_argument("--protected", help="file of verbatim spans the "
                    "constitution protects; one per line")
    ap.add_argument("--cheap-paragraphs",
                    help="reverse-outline-ranked cheap paragraphs, e.g. "
                         "'3,7' — cross-instrument convergence for "
                         "single-critic deletions")
    ap.add_argument("--model", default=os.environ.get(
        "CRITIC_APPLY_MODEL", "cohere:command-a-03-2025"))
    ap.add_argument("--endpoint", default=None)
    ap.add_argument("--dry-run", action="store_true",
                    help="decide and report; no model calls, no writes")
    ap.add_argument("--jobs", type=int, default=4,
                    help="paragraphs rewritten concurrently (default 4; 1 = "
                         "sequential). Output does not depend on it")
    a = ap.parse_args()

    text = open(a.article, encoding="utf-8").read()
    targets = parse_sheet(open(a.sheet, encoding="utf-8").read())
    protected = []
    if a.protected:
        protected = [ln.strip() for ln in open(a.protected, encoding="utf-8")
                     if ln.strip() and not ln.startswith("#")]
    cheap = set()
    if a.cheap_paragraphs:
        cheap = {int(x) for x in a.cheap_paragraphs.split(",") if x.strip()}

    generate = None
    if not a.dry_run:
        sys.path.insert(0, MATCH_VOICE)
        import rewrite as _rw

        def generate(prompt):
            kw = {"model": a.model, "temperature": 0.3}
            if a.endpoint:
                kw["endpoint"] = a.endpoint
            return _rw.generate(prompt, **kw)

    new_text, records = decide_and_apply(
        text, targets, generate=generate, protected=protected, cheap=cheap,
        jobs=a.jobs)

    out = a.out or os.path.splitext(a.article)[0] + ".applied.md"
    if not a.dry_run:
        open(out, "w", encoding="utf-8").write(new_text)
    log = out + ".critic-apply.json"
    summary = counts(records)
    json.dump({"article": a.article, "sheet": a.sheet, "model": a.model,
               "summary": summary, "targets": records},
              open(log, "w", encoding="utf-8"), indent=2)

    print(f"{'DRY RUN — ' if a.dry_run else ''}targets: {len(records)}")
    for k, v in sorted(summary["by_status"].items()):
        print(f"  {k}: {v}")
    print(f"applied: {summary['applied']}  kept: {summary['kept']}  "
          f"declined-by-rule: {summary['declined_by_rule']}")
    if not a.dry_run:
        print(f"out: {out}")
    print(f"log: {log}")


if __name__ == "__main__":
    main()
