#!/usr/bin/env python3
"""The rewrite pass is scoped to flagged paragraphs and gated before the
splice (GH-411).

Offline: rewrite_passage, the scans, and the critic are stubs; no model.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import drive  # noqa: E402

PARAS = [
    "The gateway forwards each request to the model it names and returns "
    "the reply unchanged, which keeps the billing on the provider side.",
    "The shim translates the request into the provider's native format and "
    "records the latency for the dashboard that the operators read daily.",
    "Subscribe for the next issue, and start here if you are new to the series.",
]
ARTICLE = "\n\n".join(PARAS)


def _line_of(text, needle):
    return text[:text.index(needle)].count("\n") + 1


def _scan(flag_lines):
    return {"lexical": {"issue_count": len(flag_lines),
                        "issues": [{"line": ln, "category": "ai-phrase",
                                    "text": "flagged"} for ln in flag_lines]},
            "structural": {"issue_count": 0, "issues": []},
            "verdict": "likely-ai", "needs_step3": True}


def _run(rewrite_fn, flag_lines, critic=None, scope="flagged", canonical=None):
    orig = (drive.rewrite_passage, drive.run_lexical, drive.run_structural)
    drive.rewrite_passage = rewrite_fn
    drive.run_lexical = lambda path: {"issue_count": 9, "issues": []}
    drive.run_structural = lambda path, vp=None: {"issue_count": 0, "issues": []}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            art = os.path.join(tmp, "a.md")
            with open(art, "w") as f:
                f.write(ARTICLE)
            reg = None
            if canonical:
                reg = os.path.join(tmp, "canonical-blocks.txt")
                with open(reg, "w") as f:
                    f.write(canonical + "\n")
            result = drive.run_rewrite(art, _scan(flag_lines), None, "http://unused",
                                       "test-model", 5, max_passes=1, scope=scope,
                                       critic=critic, canonical_blocks=reg)
            draft = open(result["draft_path"]).read() if "draft_path" in result else ""
            return result, draft
    finally:
        drive.rewrite_passage, drive.run_lexical, drive.run_structural = orig


L1, L2, L3 = (_line_of(ARTICLE, p[:30]) for p in PARAS)


def test_only_flagged_paragraphs_are_sent():
    sent = []

    def rw(text, issues, endpoint, model, timeout):
        sent.append(text)
        return text.replace("forwards", "passes")

    result, draft = _run(rw, [L1])
    assert sent == [PARAS[0]], sent
    assert "passes each request" in draft
    assert result["scope"] == "flagged" and result["passes"][-1]["targets"] == 1
    _, _ = _run(rw, [L1], scope="all")
    assert len(sent) == 1 + 3, "scope all restores the whole-document pass"
    print("  only_flagged_paragraphs_are_sent: ok")


def test_scaffold_line_is_stripped():
    def rw(text, issues, endpoint, model, timeout):
        return "Here's the rewritten paragraph:\n" + text.replace("forwards", "passes")

    _, draft = _run(rw, [L1])
    assert "Here's the rewritten" not in draft, draft
    assert "passes each request" in draft
    print("  scaffold_line_is_stripped: ok")


def test_introduced_banned_word_is_refused():
    def rw(text, issues, endpoint, model, timeout):
        return text.replace("forwards", "seamlessly forwards")

    result, draft = _run(rw, [L1])
    assert "seamlessly" not in draft
    p1 = result["passes"][-1]
    assert p1["gate_refused"] == 1, p1
    assert any(e["cause"] == "gate-refused" and "seamlessly" in e["error"]
               for e in p1["errors"]), p1
    print("  introduced_banned_word_is_refused: ok")


def test_invented_number_is_refused():
    def rw(text, issues, endpoint, model, timeout):
        return text.replace("each request", "each of 40 requests")

    result, draft = _run(rw, [L1])
    assert "40" not in draft
    assert result["passes"][-1]["gate_refused"] == 1
    print("  invented_number_is_refused: ok")


def test_critic_reject_keeps_the_original():
    """The gpt-oss case: a fluent rewrite that invents a fact."""
    def rw(text, issues, endpoint, model, timeout):
        return text.replace("the model it names",
                            "OpenRouter, which Anthropic and Vertex AI also use,")

    def critic(prompt):
        return json.dumps({"meaning_deltas": ["adds a claim about OpenRouter"],
                           "term_swaps": [], "register_drift": False,
                           "verdict": "reject"})

    result, draft = _run(rw, [L1], critic=critic)
    assert "OpenRouter" not in draft and PARAS[0] in draft
    assert result["critic"] == "model"
    print("  critic_reject_keeps_the_original: ok")


def test_critic_repair_gets_one_retry():
    calls = []

    def rw(text, issues, endpoint, model, timeout):
        calls.append(issues)
        if "KEEP:" in issues:
            return text.replace("forwards", "passes")
        return text.replace("returns the reply unchanged", "may return the reply")

    verdicts = iter(["repair", "accept"])

    def critic(prompt):
        v = next(verdicts)
        return json.dumps({"meaning_deltas": ["hedge added"] if v == "repair" else [],
                           "term_swaps": [], "register_drift": False, "verdict": v})

    _, draft = _run(rw, [L1], critic=critic)
    assert len(calls) == 2 and "Meaning changed: hedge added" in calls[1], calls
    assert "passes each request" in draft and "may return" not in draft
    print("  critic_repair_gets_one_retry: ok")


def test_canonical_paragraph_is_never_sent():
    sent = []

    def rw(text, issues, endpoint, model, timeout):
        sent.append(text)
        return text.replace("Subscribe", "Sign up")

    result, draft = _run(rw, [L3], canonical="Subscribe for the next issue")
    assert sent == [], sent
    assert result["canonical_held"] == 1, result
    assert "draft_path" not in result, "nothing targeted, nothing written"
    sent.clear()
    result, draft = _run(rw, [L1, L3], canonical="Subscribe for the next issue")
    assert sent == [PARAS[0]], sent
    assert PARAS[2] in draft and "Sign up" not in draft
    print("  canonical_paragraph_is_never_sent: ok")


def test_strip_scaffold_keeps_prose():
    assert drive.strip_scaffold("Here is the revised passage:\nThe gate held.") \
        == "The gate held."
    keep = "Here is the gate the team built, and it held."
    assert drive.strip_scaffold(keep) == keep
    print("  strip_scaffold_keeps_prose: ok")


def main():
    test_only_flagged_paragraphs_are_sent()
    test_scaffold_line_is_stripped()
    test_introduced_banned_word_is_refused()
    test_invented_number_is_refused()
    test_critic_reject_keeps_the_original()
    test_critic_repair_gets_one_retry()
    test_canonical_paragraph_is_never_sent()
    test_strip_scaffold_keeps_prose()
    print("test_rewrite_gate: all assertions passed")


if __name__ == "__main__":
    main()
