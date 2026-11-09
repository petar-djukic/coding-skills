#!/usr/bin/env python3
"""
drive.py — Headless driver for the filter-tells pipeline.

Orchestrates the filter-tells steps as a CLI so subagents and workflows
can invoke the pipeline without reading SKILL.md and calling each script
by hand.

Steps 1-2: lexical + structural scans (no model).
Step 3: semantic analysis via Ollama (12 perplexity prompts).
Steps 4-5: targeted rewrite of flagged passages, recursive validation.

Usage:
    python3 drive.py --article <path> --scan-only
    python3 drive.py --article <path> --no-rewrite [--model <model>]
    python3 drive.py --article <path> [--voice-profile <path>] [--out <path>]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

_DIR = os.path.dirname(os.path.realpath(__file__))
_SKILL = os.path.normpath(os.path.join(_DIR, ".."))
_PROMPTS_PATH = os.path.join(_SKILL, "references", "perplexity-prompts.md")
_FM = re.compile(r"\A---\s*\n.*?\n(?:---|\.\.\.)\s*\n", re.DOTALL)

DEFAULT_ENDPOINT = os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434")
# Operator decision (GH-176, 2026-08-31): default is Cohere, overriding the
# GH-170 post-fix mean where gpt-oss led (0.114 vs 0.279). Recorded as a
# choice, not a measurement: Cohere was best-in-run on technical prose
# (including the run's only perfect 0.000/0.931 score) and improved most once
# GH-171/172 fixed the pipeline faults that had depressed it. It is a hosted
# API — needs a key, bills per token, sends the draft off the machine; a
# keyless machine sets FILTER_TELLS_MODEL=gpt-oss:120b-cloud, the GH-170
# incumbent, and check_server names that remediation rather than crashing.
DEFAULT_MODEL = os.environ.get("FILTER_TELLS_MODEL", "cohere:command-a-03-2025")
DEFAULT_TIMEOUT = int(os.environ.get("FILTER_TELLS_TIMEOUT", "600"))


# ---------------------------------------------------------------------------
# Ollama client (imported from match-voice when available, inline fallback)
# ---------------------------------------------------------------------------

def _import_generate():
    """Import generate() from match-voice/scripts/rewrite.py."""
    mv = os.path.normpath(os.path.join(_DIR, "..", "..", "match-voice", "scripts"))
    if mv not in sys.path:
        sys.path.insert(0, mv)
    try:
        from rewrite import generate, check_server
        return generate, check_server
    except ImportError:
        return None, None


_generate_fn, _check_server_fn = _import_generate()


def generate(prompt: str, endpoint: str = DEFAULT_ENDPOINT,
             model: str = DEFAULT_MODEL, timeout: int = DEFAULT_TIMEOUT) -> str:
    if _generate_fn is not None:
        return _generate_fn(prompt, endpoint=endpoint, model=model,
                            temperature=0.3, timeout=timeout)
    raise RuntimeError(
        "Could not import generate() from match-voice/scripts/rewrite.py. "
        "Ensure the skill set is complete.")


def check_server(endpoint: str, model: str) -> tuple[bool, str]:
    if _check_server_fn is not None:
        return _check_server_fn(endpoint, model)
    return False, "check_server not importable"


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------

def load_prompts() -> dict[str, str]:
    """Parse perplexity-prompts.md into {prompt_id: template_text}."""
    with open(_PROMPTS_PATH) as f:
        text = f.read()
    prompts = {}
    blocks = re.split(r"^## Prompt (\d+\w?):", text, flags=re.MULTILINE)
    for i in range(1, len(blocks), 2):
        pid = blocks[i].strip()
        body = blocks[i + 1]
        code = re.findall(r"```\n(.*?)```", body, re.DOTALL)
        if code:
            prompts[pid] = code[0].strip()
    return prompts


# ---------------------------------------------------------------------------
# Steps 1-2: lexical + structural scans
# ---------------------------------------------------------------------------

def run_lexical(article: str) -> dict:
    """Run detect-lexical.sh --json and parse its output."""
    script = os.path.join(_DIR, "detect-lexical.sh")
    proc = subprocess.run(
        ["bash", script, article, "--json"],
        capture_output=True, text=True)
    if proc.returncode == 2:
        return {"error": proc.stderr.strip(), "exit_code": 2,
                "issues": [], "candidates": []}
    try:
        hits = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"error": "failed to parse lexical JSON",
                "raw": proc.stdout[:500], "exit_code": proc.returncode,
                "issues": [], "candidates": []}
    issues = [h for h in hits if h.get("severity") != "candidate"]
    candidates = [h for h in hits if h.get("severity") == "candidate"]
    return {"exit_code": proc.returncode, "issues": issues,
            "candidates": candidates}


def run_structural(article: str, voice_profile: str | None = None) -> dict:
    """Run detect-structural.py --json and return its parsed dict."""
    script = os.path.join(_DIR, "detect-structural.py")
    cmd = [sys.executable, script, article, "--json"]
    if voice_profile:
        cmd.append(f"--voice-profile={voice_profile}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 2:
        return {"error": proc.stderr.strip(), "exit_code": 2,
                "verdict": "error", "issues": [], "metrics": {}}
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"error": "failed to parse structural JSON",
                "raw": proc.stdout[:500], "exit_code": proc.returncode,
                "verdict": "error", "issues": [], "metrics": {}}
    result["exit_code"] = proc.returncode
    return result


def combine(lexical: dict, structural: dict) -> dict:
    """Merge lexical and structural results into a single scan summary."""
    lex_issues = lexical.get("issues", [])
    lex_candidates = lexical.get("candidates", [])
    struct_issues = structural.get("issues", [])
    struct_verdict = structural.get("verdict", "error")

    has_issues = bool(lex_issues) or bool(struct_issues)
    if structural.get("error") or lexical.get("error"):
        verdict = "error"
    elif has_issues:
        verdict = struct_verdict if struct_verdict in (
            "likely-ai", "suspicious", "suspicious-overshoot"
        ) else "issues-found"
    else:
        verdict = struct_verdict

    categories = {}
    for hit in lex_issues:
        cat = hit.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "verdict": verdict,
        "needs_step3": verdict not in ("clean", "error"),
        "lexical": {
            "exit_code": lexical.get("exit_code", -1),
            "issue_count": len(lex_issues),
            "candidate_count": len(lex_candidates),
            "categories": categories,
            "issues": lex_issues,
            "candidates": lex_candidates,
        },
        "structural": {
            "exit_code": structural.get("exit_code", -1),
            "verdict": struct_verdict,
            "issue_count": len(struct_issues),
            "issues": struct_issues,
            "metrics": structural.get("metrics", {}),
            "advisory": structural.get("advisory", []),
            "repeated_formulae": structural.get("repeated_formulae", []),
            "coinage_candidates": structural.get("coinage_candidates", []),
        },
    }


# ---------------------------------------------------------------------------
# Step 3: semantic analysis via Ollama
# ---------------------------------------------------------------------------

def _fmt_issues(issues: list) -> str:
    """Format issues list as a readable summary for prompt injection."""
    if not issues:
        return "(none)"
    lines = []
    for h in issues[:30]:
        cat = h.get("category", h.get("type", ""))
        line = h.get("line", h.get("position", ""))
        text = h.get("text", h.get("detail", ""))[:120]
        lines.append(f"  L{line} [{cat}] {text}")
    return "\n".join(lines)


def _fmt_metrics(metrics: dict) -> str:
    if not metrics:
        return "(none)"
    return "\n".join(f"  {k}: {v}" for k, v in metrics.items())


def _filter_hits(candidates: list, category: str) -> str:
    hits = [h for h in candidates if h.get("category") == category]
    if not hits:
        return "(none)"
    return "\n".join(f"  L{h.get('line','')} {h.get('text','')[:100]}"
                     for h in hits[:15])


def _meta_narration_hits(candidates: list) -> str:
    """The tight meta-narration hits, then the loose ones labelled as lower
    priority (GH-408): the loose patterns fire on human prose about as often
    as on AI prose, so the prompt must not weigh them alike."""
    tight = _filter_hits(candidates, "meta-narration")
    loose = _filter_hits(candidates, "meta-narration-loose")
    if loose == "(none)":
        return tight
    return (tight + "\n  Lower priority (these patterns fire on human prose "
            "as often as on AI prose; flag only on the addressee test):\n" + loose)


def run_semantic(article_text: str, scan: dict, prompts: dict,
                 endpoint: str, model: str, timeout: int) -> dict:
    """Run Step 3 prompts in the order specified by SKILL.md/prompt-catalog."""
    results = {}
    lex = scan.get("lexical", {})
    struct = scan.get("structural", {})
    metrics = struct.get("metrics", {})

    def call(pid: str, extra_vars: dict | None = None) -> str | None:
        tmpl = prompts.get(pid)
        if tmpl is None:
            return None
        variables = {"text": article_text}
        if extra_vars:
            variables.update(extra_vars)
        filled = tmpl
        for k, v in variables.items():
            filled = filled.replace("{" + k + "}", str(v))
        # Clear unfilled placeholders
        filled = re.sub(r"\{[a-z_]+\}", "(not available)", filled)
        try:
            return generate(filled, endpoint=endpoint, model=model,
                            timeout=timeout)
        except RuntimeError as e:
            return f"[error] {e}"

    # Prompt 0: cold read (first, before anything else)
    results["prompt_0"] = call("0")

    # Prompts 1-3: independent assessments (sequential in this driver)
    results["prompt_1"] = call("1")
    results["prompt_2"] = call("2")
    results["prompt_3"] = call("3")

    # Prompt 4: CoT leakage detection (after lexical results)
    results["prompt_4"] = call("4")

    # Prompt 6 + 6b: antithesis and set-piece enumeration (after structural)
    results["prompt_6"] = call("6")
    results["prompt_6b"] = call("6b")

    # Prompt 7: overshoot assessment (after structural, seeded with metrics)
    perf_metrics = {k: v for k, v in metrics.items()
                    if k in ("plain_sentence_rate", "intensity_variance",
                             "mean_performance_score")}
    results["prompt_7"] = call("7", {
        "performance_metrics": _fmt_metrics(perf_metrics),
        "punch_candidates": _fmt_issues(
            [i for i in struct.get("issues", [])
             if "punch" in i.get("type", "")]),
        "salad_candidates": _fmt_issues(
            [i for i in struct.get("issues", [])
             if "salad" in i.get("type", "")]),
        "repeated_formulae": json.dumps(
            struct.get("repeated_formulae", [])[:10], indent=2),
        "ornate_hits": _filter_hits(
            lex.get("candidates", []), "ornate-register"),
        "voice_anchors": "(not available)",
    })

    # Prompt 8 + 8b: definedness/circularity and empty phrases
    results["prompt_8"] = call("8")
    coinage = struct.get("coinage_candidates", [])
    results["prompt_8b"] = call("8b", {
        "coinage_candidates": json.dumps(coinage[:10], indent=2)
            if coinage else "(none)",
        "editorializing_hits": _filter_hits(
            lex.get("candidates", []), "editorializing"),
        "reader_directive_hits": _filter_hits(
            lex.get("candidates", []), "reader-directive"),
        "meta_narration_hits": _meta_narration_hits(lex.get("candidates", [])),
    })

    # Prompt 9: paragraph schema (seeded by structural metrics)
    schema_metrics = {k: v for k, v in metrics.items()
                      if k in ("topic_overlap", "cohesion", "subject_churn")}
    results["prompt_9"] = call("9", {
        "schema_metrics": _fmt_metrics(schema_metrics)
            if schema_metrics else "(no paragraph schema proxies available)",
    })

    # Prompt 5: integrator — runs LAST with all evidence
    results["prompt_5"] = call("5", {
        "lexical_results": _fmt_issues(lex.get("issues", [])),
        "structural_results": (
            f"Verdict: {struct.get('verdict', 'unknown')}\n"
            f"Issues: {_fmt_issues(struct.get('issues', []))}\n"
            f"Metrics: {_fmt_metrics(metrics)}"),
        "perplexity_results": "\n".join(
            f"Prompt {k}: {(v or '')[:200]}"
            for k, v in sorted(results.items())
            if k.startswith("prompt_") and k not in ("prompt_5",)),
        "cot_results": (results.get("prompt_4") or "(not run)")[:500],
        "overshoot_results": (results.get("prompt_7") or "(not run)")[:500],
    })

    # Extract rewrite priority from Prompt 5 output
    priority = _extract_priority(results.get("prompt_5", ""))

    # Extract overall verdict signals from Prompt 5
    ai_prob = _extract_field(results.get("prompt_5", ""), "AI_PROBABILITY")
    confidence = _extract_field(results.get("prompt_5", ""), "CONFIDENCE")
    cold_verdict = _extract_field(results.get("prompt_0", ""), "COLD_VERDICT")

    return {
        "prompts_run": [k.replace("prompt_", "") for k in sorted(results)
                        if results[k] is not None],
        "cold_verdict": cold_verdict,
        "ai_probability": ai_prob,
        "confidence": confidence,
        "rewrite_priority": priority,
        "prompt_results": results,
    }


def _extract_priority(text: str) -> list[str]:
    """Extract REWRITE_PRIORITY lines from Prompt 5 output."""
    if not text:
        return []
    m = re.search(r"REWRITE_PRIORITY[:\s]*(.*?)(?:\n\n|\Z)",
                  text, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    block = m.group(1).strip()
    # Cohere bolds its labels, leaving "**" residue on the values and a bare
    # "**" line where the label's own bold closed (GH-180). Strip markdown
    # emphasis from the edges and drop lines that were only emphasis.
    lines = [ln.strip().lstrip("0123456789.-) ").strip("*").strip()
             for ln in block.split("\n")
             if ln.strip() and not ln.strip().startswith("---")]
    return [ln for ln in lines if ln]


def _extract_field(text: str, field: str) -> str:
    """Extract a labeled field value from prompt output."""
    if not text:
        return ""
    m = re.search(rf"{field}[:\s]+(.+?)(?:\n|$)", text, re.IGNORECASE)
    return m.group(1).strip().strip("*").strip() if m else ""


# ---------------------------------------------------------------------------
# Paragraph extraction (shared scripts directory)
# ---------------------------------------------------------------------------

def _import_md_paragraphs():
    shared = os.path.normpath(os.path.join(_DIR, "..", "..", "..", "scripts"))
    if shared not in sys.path:
        sys.path.insert(0, shared)
    try:
        import md_paragraphs
        return md_paragraphs
    except ImportError:
        return None


def parse_paragraphs(article: str) -> list[list]:
    """Extract prose paragraphs as [[start_line, end_line, text], ...].

    Uses md_paragraphs.parse_file from the shared scripts directory.
    """
    mp = _import_md_paragraphs()
    if mp is None:
        raise RuntimeError(
            "md_paragraphs.py not found in scripts/")
    result = mp.parse_file(article)
    return result.paragraphs


# ---------------------------------------------------------------------------
# Steps 4-5: targeted rewrite and recursive validation
# ---------------------------------------------------------------------------

_REWRITE_PROMPT = """\
You are rewriting a passage to remove AI writing patterns while \
preserving exact meaning and matching the author's voice.

DETECTED ISSUES IN THIS PASSAGE:
{issue_report}

AUTHOR'S STYLE:
- Concise, active voice, Strunk & White style
- Specific and concrete, no vague qualifiers
- Takes positions, avoids hedging
- Varied sentence rhythm
- Technical precision without jargon inflation

PASSAGE TO REWRITE:
{passage}

CONSTRAINTS:
1. Fix ONLY the flagged issues
2. Preserve all technical meaning
3. Do NOT introduce any patterns from the banned list
4. Vary sentence length (target std > 5)
5. Do NOT use mechanical transitions
6. Do NOT hedge or both-sides
7. Sound like a human expert wrote this in one draft
8. Plain sentences are allowed and required
9. Do NOT close every paragraph on a flourish
10. Prefer the boring accurate sentence over the clever compressed one
11. Copy every bracketed citation marker (a number or an @-key in square \
brackets) into the rewrite verbatim, attached to the same claim; never add \
one that is not already there
12. The rewrite must not be longer than the original passage — cutting is \
allowed, adding is not
13. Preserve every bold, italic, and backtick code span in place
14. A flagged paired-universal ("every X and every Y") keeps one quantifier \
or none: "for each agent's tasks", or drop "every" where the sentence is \
already general

OUTPUT: The rewritten passage only. No commentary."""


_QUOTED = re.compile(r'[\u201c"]([^\u201c\u201d"]{12,})[\u201d"]')


def _issues_for_lines(scan: dict, start: int, end: int, passage: str = "") -> str:
    """Collect scan issues that belong to THIS passage.

    Lexical issues carry line numbers and filter by range. Structural issues
    carry sentence-pair positions that do not map to lines, so they are kept
    only when the verbatim prose their detail quotes appears in the passage;
    a quote-less detail (a document-level rhythm stat like dash-heavy) is kept
    everywhere.

    Before GH-171 the structural list was appended to EVERY paragraph's
    rewrite prompt, quotes and all — 26 issues, 2,815 characters of other
    paragraphs' sentences, injected into each of ~70 rewrites of one essay.
    An instruction-literal model then "fixes" prose that is not in its
    passage: one bake-off draft came back with a sentence quoted in an issue
    detail spliced into six different paragraphs, and a vocabulary the issue
    blob converged every paragraph onto. Models that ignore prompt noise hid
    the bug; models that obey exposed it."""
    hits = []
    for h in scan.get("lexical", {}).get("issues", []):
        ln = h.get("line", 0)
        if start <= ln <= end:
            hits.append(f"L{ln} [{h.get('category','')}] {h.get('text','')[:100]}")
    passage_flat = " ".join(passage.split()).lower()
    for h in scan.get("structural", {}).get("issues", []):
        detail = h.get("detail", "")
        quotes = _QUOTED.findall(detail)
        if quotes:
            if not passage_flat:
                continue
            if not any(" ".join(q.split()).lower() in passage_flat for q in quotes):
                continue
        hits.append(f"[{h.get('type','')}] {detail[:100]}")
    return "\n".join(hits) if hits else "(general AI patterns detected)"


# Pandoc [@key], numbered [1], and \citep{...}/\citet{...} markers. The gate
# compares multisets by identity: a rewrite that swaps [@park2024] for any
# other key — including a plausible-looking one — is damage, not preservation.
# match-voice's verify.py has enforced this per paragraph all along; the
# filter-tells splice had no citation check at all (GH-159).
_CITE_MARKERS = re.compile(r"\[@[^\]\s]+\]|\[\d+\]|\\cite[pt]?\{[^}]*\}")


def _citation_damage(original: str, rewritten: str) -> str | None:
    """A sentence naming what changed, or None when the markers survive."""
    from collections import Counter
    o, r = Counter(_CITE_MARKERS.findall(original)), Counter(_CITE_MARKERS.findall(rewritten))
    if o == r:
        return None
    lost = sorted((o - r).elements())
    invented = sorted((r - o).elements())
    parts = []
    if lost:
        parts.append(f"lost {', '.join(lost)}")
    if invented:
        parts.append(f"invented {', '.join(invented)}")
    return "citation markers damaged: " + "; ".join(parts)


def rewrite_passage(passage: str, issue_report: str,
                    endpoint: str, model: str, timeout: int) -> str:
    """Send a passage through the rewrite prompt via Ollama."""
    prompt = _REWRITE_PROMPT.format(passage=passage, issue_report=issue_report)
    return generate(prompt, endpoint=endpoint, model=model, timeout=timeout)


# ---------------------------------------------------------------------------
# The splice gate (GH-411)
# ---------------------------------------------------------------------------
# On tight post-pipeline drafts this pass corrupted meaning with nothing to
# stop it: Cohere leaked prompt diction ("critical", "key", "seamlessly") and
# deleted canonical lines, gpt-oss invented a fact ("Anthropic and Vertex AI
# use the OpenAI-compatible interface of OpenRouter"), and a literal "Here's
# the rewritten paragraph:" reached the draft. match-voice gated the same
# payloads cleanly, so this pass now borrows its gates rather than growing a
# parallel set: verify.verify (citations, numbers, markup, quoted spans,
# dashes, introduced first person), critique.mechanical (introduced banned
# words, new antithesis or tricolon, protected-term loss), and, when a critic
# is supplied, critique's model-judged meaning entailment with one repair.

_SCAFFOLD = re.compile(
    r"^\s*(?:here'?s|here is|below is|this is)\b[^\n]{0,60}"
    r"\b(?:rewrit\w*|revis\w*|paragraph|passage|version)\b[^\n]*:\s*$"
    r"|^\s*(?:rewritten|revised) (?:paragraph|passage|text)\s*:\s*$",
    re.IGNORECASE | re.MULTILINE)


def strip_scaffold(text: str) -> str:
    """Drop lead-in lines a model emits around the rewrite."""
    return _SCAFFOLD.sub("", text).strip()


def _gate_modules():
    mv = os.path.normpath(os.path.join(_DIR, "..", "..", "match-voice", "scripts"))
    if mv not in sys.path:
        sys.path.insert(0, mv)
    import critique
    import protected_terms
    import verify
    return verify, critique, protected_terms


def gate(original: str, candidate: str, protected: list | None = None,
         banned: list | None = None, critic=None) -> dict:
    """Decide one rewrite. Returns {"verdict": accept|repair|reject,
    "reasons": [...], "critique": {...}}. Mechanical findings are never
    waived; the critic, when present, can only add findings."""
    verify, critique, _ = _gate_modules()
    v = verify.verify(original, candidate, protected_terms=protected or [])
    fatal = [f["detail"] for f in v["findings"] if f["severity"] == "fatal"]
    if fatal:
        return {"verdict": "reject", "reasons": fatal, "critique": None}
    crit = critique.critique(original, candidate, protected_terms=protected or [],
                             banned=banned, generate=critic)
    reasons = []
    for key in ("banned_words", "quoted_span_changes"):
        reasons += [f"{key}: {x}" for x in crit.get(key) or []]
    reasons += [f"term lost: {t['from']}" for t in crit.get("term_swaps") or []]
    if crit.get("new_antithesis"):
        reasons.append("staged a contrast the original did not have")
    if crit.get("new_nominalization"):
        reasons.append("raised nominalizations over the original")
    if crit.get("new_colon"):
        reasons.append("added a colon the original did not have")
    if crit.get("new_tricolon"):
        reasons.append("added a three-item list the original did not have")
    reasons += [f"meaning: {d}" for d in crit.get("meaning_deltas") or []]
    if crit.get("register_drift"):
        reasons.append("register drift")
    verdict = crit["verdict"] if critic is not None else ("repair" if reasons else "accept")
    return {"verdict": verdict, "reasons": reasons, "critique": crit}


def _rewrite_error_cause(msg: str) -> str:
    """Bucket a rewrite error into a cause, mirroring match-voice's
    classify_rewrite_error so the two skills report failures in the same
    vocabulary. Local rather than imported: match-voice's copy lives in its
    driver script, and importing a driver for one dictionary couples the
    skills at the wrong joint."""
    m = (msg or "").lower()
    if "empty output" in m:
        return "empty/sanitized-to-empty"
    if "refusing" in m or "denylist" in m:
        return "refused-model"
    if "api key" in m:
        return "no-api-key"
    if "unreachable" in m:
        return "server-unreachable"
    if "timed out" in m or "timeout" in m:
        return "timeout"
    if "http" in m or "request failed" in m:
        return "api-error"
    return "other"


# Causes that will recur identically for every paragraph: a refused model, a
# missing key, an unreachable server. One of these stops the run; anything
# else costs only its own paragraph (GH-157).
RUN_FATAL_CAUSES = frozenset({"refused-model", "no-api-key", "server-unreachable"})


def run_rewrite(article_path: str, scan: dict, semantic: dict | None,
                endpoint: str, model: str, timeout: int,
                voice_profile: str | None = None,
                max_passes: int = 3, scope: str = "flagged",
                critic=None, canonical_blocks: str | None = None,
                jobs: int = 4) -> dict:
    """Steps 4-5: rewrite flagged passages and validate recursively.

    scope "flagged" (the default, GH-411) rewrites only paragraphs the scan
    names; "all" also takes every paragraph of a likely-ai document, the
    pre-GH-411 behaviour. Every candidate passes gate() before it is
    spliced; `critic` (prompt -> text) adds the model-judged entailment
    check and one repair attempt. Canonical-block paragraphs are never
    sent."""
    _, critique_mod, pt = _gate_modules()
    banned = critique_mod.load_banned()
    canonical_patterns, canonical_path = pt.load_canonical(canonical_blocks, article_path)
    terms_path = pt.path_for(article_path)
    protected = pt.read_terms(terms_path) if os.path.exists(terms_path) else []
    with open(article_path) as f:
        original_text = f.read()

    fm_match = _FM.match(original_text)
    front_matter = fm_match.group(0) if fm_match else ""
    lines = original_text.split("\n")

    try:
        paras = parse_paragraphs(article_path)
    except RuntimeError as e:
        return {"error": str(e), "passes": []}

    if not paras:
        return {"error": "no paragraphs extracted", "passes": []}

    def pick(paragraphs, scan_now, first_pass):
        """Targets for a pass, and how many canonical paragraphs were held."""
        chosen, held = [], 0
        for start, end, text in paragraphs:
            if canonical_patterns and pt.is_canonical(text, canonical_patterns):
                held += 1
                continue
            issues = _issues_for_lines(scan_now, start, end, text)
            flagged = issues != "(general AI patterns detected)"
            whole_doc = (first_pass and scope == "all" and scan_now.get("verdict") in
                         ("likely-ai", "suspicious", "suspicious-overshoot"))
            if flagged or whole_doc:
                chosen.append((start, end, text, issues))
        return chosen, held

    targets, canonical_held = pick(paras, scan, True)

    if not targets:
        return {"rewrites": 0, "passes": [], "scope": scope,
                "canonical_held": canonical_held,
                "message": "no passages targeted for rewrite"}

    out_dir = os.path.dirname(os.path.abspath(article_path))
    base = os.path.splitext(os.path.basename(article_path))[0]
    draft_path = os.path.join(out_dir, f"{base}.ft-draft.md")
    passes = []
    prev_issue_count = (scan["lexical"]["issue_count"] +
                        scan["structural"]["issue_count"])
    # Seed the draft with the original. Every pass then reads and writes THIS
    # file, so the paragraph positions in `targets` (re-derived from the same
    # file each pass) always match the buffer being spliced. The prior version
    # carried a stale in-memory `current_lines` across passes and spliced a
    # multi-line rewrite in as a single list element, so after pass 1 the list
    # was no longer one-line-per-element and every later index was wrong —
    # progressive corruption that ballooned the draft (GH-147).
    with open(draft_path, "w") as f:
        f.write(original_text)

    for pass_num in range(1, max_passes + 1):
        # Read the current draft fresh so splice indices match `targets`.
        current_lines = open(draft_path).read().split("\n")
        rewrites_applied = 0
        # One paragraph's failure costs that paragraph, not the pass: before
        # GH-157 a single RuntimeError broke out of this loop and silently
        # left every remaining paragraph unprocessed, with one bare error
        # string in the pass record. match-voice already isolates failures
        # per paragraph; this matches it. Only a cause that must recur for
        # every paragraph (RUN_FATAL_CAUSES) stops the run.
        errors = []
        fatal = None
        gate_refused = 0

        def _candidate(target):
            """One target's gated candidate. Returns ("ok", text),
            ("error", record, cause), ("refused", record), ("same",), or
            ("not-attempted",) once a run-fatal cause has stopped the pass."""
            start, end, text, issues = target
            if stop.is_set():
                return ("not-attempted",)
            try:
                rewritten = rewrite_passage(text, issues,
                                            endpoint, model, timeout)
            except RuntimeError as e:
                cause = _rewrite_error_cause(str(e))
                if cause in RUN_FATAL_CAUSES:
                    stop.set()
                return ("error", {"line": start, "cause": cause,
                                  "error": str(e)[:200]}, cause)
            rewritten = strip_scaffold(rewritten or "")
            if not rewritten or rewritten.strip() == text.strip():
                return ("same",)
            damage = _citation_damage(text, rewritten)
            if damage:
                # The rewrite is refused, the original paragraph stays.
                return ("refused", {"line": start, "cause": "citation-damage",
                                    "error": damage})
            g = gate(text, rewritten, protected, banned, critic)
            if g["verdict"] == "repair" and critic is not None:
                constraints = critique_mod.render_constraints(g["critique"])
                try:
                    second = strip_scaffold(rewrite_passage(
                        text, issues + "\nKEEP: " + constraints,
                        endpoint, model, timeout) or "")
                except RuntimeError as e:
                    second = ""
                    g["reasons"].append(f"repair failed: {str(e)[:120]}")
                if second and second.strip() != text.strip():
                    g2 = gate(text, second, protected, banned, critic)
                    if g2["verdict"] == "accept":
                        rewritten, g = second, g2
                    else:
                        g = {**g2, "verdict": "reject"}
                else:
                    g = {**g, "verdict": "reject"}
            if g["verdict"] != "accept":
                return ("refused", {"line": start, "cause": "gate-refused",
                                    "error": "; ".join(g["reasons"])[:300]},
                        "gate")
            return ("ok", rewritten)

        # Candidates are independent, so they are computed concurrently
        # (GH-433); the first runs alone so a run-fatal cause (no key, a
        # refused model, a dead server) costs one call, as it did when the
        # loop was sequential. The splice below stays sequential and
        # bottom-up.
        import threading
        stop = threading.Event()
        order = list(reversed(targets))
        outcomes = [_candidate(order[0])] if order else []
        rest = order[1:]
        if stop.is_set():
            outcomes += [("not-attempted",)] * len(rest)
        elif jobs <= 1 or len(rest) <= 1:
            outcomes += [_candidate(t) for t in rest]
        else:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=jobs) as pool:
                outcomes += list(pool.map(_candidate, rest))

        for (start, end, text, issues), out in zip(order, outcomes):
            kind = out[0]
            if kind == "error":
                errors.append(out[1])
                if out[2] in RUN_FATAL_CAUSES and fatal is None:
                    fatal = out[2]
            elif kind == "refused":
                errors.append(out[1])
                if len(out) > 2:
                    gate_refused += 1
            elif kind == "ok":
                # Expand a multi-line rewrite into multiple list elements, or
                # current_lines stops being one-line-per-element. reversed()
                # (bottom-up) keeps earlier indices valid even when a rewrite
                # changes the paragraph's line count.
                current_lines[start - 1:end] = out[1].split("\n")
                rewrites_applied += 1

        with open(draft_path, "w") as f:
            f.write("\n".join(current_lines))

        # Validate by re-running Steps 1-2 on the written draft.
        lex = run_lexical(draft_path)
        struct = run_structural(draft_path, voice_profile)
        val = combine(lex, struct)
        new_count = val["lexical"]["issue_count"] + val["structural"]["issue_count"]

        pass_record = {
            "pass": pass_num,
            "targets": len(targets),
            "rewrites_applied": rewrites_applied,
            "gate_refused": gate_refused,
            "issue_count": new_count,
            "prev_issue_count": prev_issue_count,
            "verdict": val["verdict"],
        }
        if errors:
            pass_record["errors"] = errors
        passes.append(pass_record)

        if fatal:
            # The paragraphs already rewritten this pass are kept — the draft
            # was written above — but nothing further can succeed.
            pass_record["stopped"] = f"fatal: {fatal}"
            break
        if val["verdict"] == "clean":
            break
        if new_count >= prev_issue_count:
            pass_record["stopped"] = "no improvement"
            break

        prev_issue_count = new_count
        # Re-parse + re-target from the written draft for the next pass.
        try:
            paras = parse_paragraphs(draft_path)
        except RuntimeError:
            break
        targets, _ = pick(paras, val, False)
        if not targets:
            break

    return {
        "draft_path": draft_path,
        "scope": scope,
        "critic": "model" if critic is not None else "mechanical only",
        "canonical_held": canonical_held,
        "canonical_blocks": canonical_path,
        "passes": passes,
        "before": {"issue_count": (scan["lexical"]["issue_count"] +
                                   scan["structural"]["issue_count"]),
                   "verdict": scan["verdict"]},
        "after": {"issue_count": passes[-1]["issue_count"] if passes else 0,
                  "verdict": passes[-1]["verdict"] if passes else scan["verdict"]},
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="filter-tells headless driver")
    ap.add_argument("--article", required=True,
                    help="Path to the markdown file to analyze")
    ap.add_argument("--scan-only", action="store_true",
                    help="Run Steps 1-2 only, print JSON, and exit")
    ap.add_argument("--voice-profile",
                    help="Path to a voice-profile.json for distance check")
    ap.add_argument("--out", help="Write JSON output to this file")
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help=f"Model for semantic analysis (default: {DEFAULT_MODEL})")
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT,
                    help=f"Ollama endpoint (default: {DEFAULT_ENDPOINT})")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                    help=f"Per-prompt timeout in seconds (default: {DEFAULT_TIMEOUT})")
    ap.add_argument("--no-rewrite", action="store_true",
                    help="Run Steps 1-3, report only, skip rewrite passes")
    ap.add_argument("--jobs", type=int,
                    default=int(os.environ.get("FILTER_TELLS_JOBS", "4")),
                    help="paragraphs rewritten concurrently (default 4, or "
                         "FILTER_TELLS_JOBS; 1 = sequential). The draft does "
                         "not depend on it")
    ap.add_argument("--rewrite-scope", choices=["flagged", "all"], default="flagged",
                    help="flagged (default): rewrite only paragraphs the scan "
                         "names; all: every paragraph of a likely-ai document "
                         "(pre-GH-411 behaviour)")
    ap.add_argument("--critic-model",
                    help="model for the entailment critique of each rewrite "
                         "(default: --model)")
    ap.add_argument("--no-critique", action="store_true",
                    help="gate rewrites mechanically only; no entailment model call")
    ap.add_argument("--canonical-blocks", metavar="FILE",
                    help="canonical-block registry (default: writing-voice/"
                         "canonical-blocks.txt found walking up)")
    ap.add_argument("--voice-dir",
                    help="Path to writing-voice/ directory (future)")
    ap.add_argument("--lexicon",
                    choices=["newsletter", "book", "industry", "academic",
                             "none"],
                    help="Venue lexicon for the lexical scan (GH-337); "
                         "usually a venue profile's tell_lexicon value. "
                         "Default: newsletter.")
    args = ap.parse_args()

    # Exported rather than threaded: detect-lexical.sh reads
    # FILTER_TELLS_LEXICON as its default, so the re-scan inside the rewrite
    # loop uses the same lexicon without every caller passing it down.
    if args.lexicon:
        os.environ["FILTER_TELLS_LEXICON"] = args.lexicon

    if not os.path.isfile(args.article):
        print(f"Error: file not found: {args.article}", file=sys.stderr)
        sys.exit(2)

    # Steps 1-2: lexical + structural scans
    lexical = run_lexical(args.article)
    structural = run_structural(args.article, args.voice_profile)
    scan = combine(lexical, structural)

    if args.scan_only:
        output = json.dumps(scan, indent=2)
        if args.out:
            with open(args.out, "w") as f:
                f.write(output + "\n")
        else:
            print(output)
        sys.exit(0 if scan["verdict"] == "clean" else
                 2 if scan["verdict"] == "error" else 1)

    # Step 3: semantic analysis (skip when clean)
    semantic = None
    server_ok = False
    if scan["needs_step3"]:
        ok, msg = check_server(args.endpoint, args.model)
        if not ok:
            print(f"Error: {msg}", file=sys.stderr)
            scan["step3_error"] = msg
        else:
            server_ok = True
            prompts = load_prompts()
            with open(args.article) as f:
                article_text = f.read()
            semantic = run_semantic(article_text, scan, prompts,
                                   args.endpoint, args.model, args.timeout)
            scan["semantic"] = semantic

    if args.no_rewrite:
        output = json.dumps(scan, indent=2)
        if args.out:
            with open(args.out, "w") as f:
                f.write(output + "\n")
        else:
            print(output)
        sys.exit(0 if scan["verdict"] == "clean" else
                 2 if scan["verdict"] == "error" else 1)

    # Steps 4-5: targeted rewrite and recursive validation
    rewrite_result = None
    if scan["verdict"] != "clean" and server_ok:
        critic = None
        if not args.no_critique:
            critic_model = args.critic_model or args.model

            def critic(prompt, _m=critic_model):
                return generate(prompt, endpoint=args.endpoint, model=_m,
                                timeout=args.timeout)
        rewrite_result = run_rewrite(
            args.article, scan, semantic,
            args.endpoint, args.model, args.timeout,
            voice_profile=args.voice_profile, scope=args.rewrite_scope,
            critic=critic, canonical_blocks=args.canonical_blocks,
            jobs=args.jobs)
        scan["rewrite"] = rewrite_result

    result = scan
    output = json.dumps(result, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(output + "\n")
    else:
        print(output)

    if result["verdict"] == "error":
        sys.exit(2)
    elif result["verdict"] == "clean":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
