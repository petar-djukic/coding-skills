#!/usr/bin/env python3
"""Offline tests for critic-apply (GH-206): convergent-applied,
split-skipped, constitution-declined, remedy-conflict-omission, marker
round-trip, gate rejection, cross-instrument deletion. No model calls —
generate is a stub."""
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import importlib
ca = importlib.import_module("critic_apply")

ARTICLE = """# Title

<!-- rst: nucleus | the thesis --> The system costs 42 dollars per run and the price is stated once [3]. The follow-up sentence restates what the price already showed.

The second paragraph stands alone and says one plain thing.

Trying to size a business that does not exist reveals nothing about whether it will ever exist.

The bridge sentence carries the constitution and must never change.
"""


def sheet(convergent_blocks="", single_blocks=""):
    return (f"# Critic panel sheet\n\n## Diagnoses\n\nx\n\n"
            f"## Convergent (n)\n\n{convergent_blocks}\n"
            f"## Single-critic suggestions\n\n{single_blocks}\n")


def conv(quote, entries):
    lines = [f'### "{quote}"', ""]
    for c, b, w in entries:
        lines.append(f"- **{c}:** {b} — *{w}*")
    return "\n".join(lines) + "\n\n"


def test_convergent_applied_and_marker_roundtrip():
    q = ("The follow-up sentence restates what the price already showed.")
    sh = sheet(conv(q, [("levine", "Cut the restatement to one clause.",
                         "the fact earns the laugh alone"),
                        ("didion", "Tighten it.", "restatement spends it")]))
    prompts = []

    def fake_generate(prompt):
        prompts.append(prompt)
        # a valid candidate: numbers and citation intact, shorter
        return ("The system costs 42 dollars per run and the price is "
                "stated once [3]. The restatement goes.")

    new, recs = ca.decide_and_apply(
        ARTICLE, ca.parse_sheet(sh), generate=fake_generate)
    assert recs[0]["status"] == "applied-rewrite", recs
    # marker round-trip: never in the prompt, still in the output
    assert "rst:" not in prompts[0], prompts[0]
    assert "<!-- rst: nucleus" in new
    assert "The restatement goes." in new
    print("  convergent_applied + marker_roundtrip: ok")


def test_split_panel_skipped():
    q = "The second paragraph stands alone and says one plain thing."
    sh = sheet(conv(q, [("levine", "CUT", "does nothing"),
                        ("hemingway", "KEEP — it earns its place",
                         "the plainness is the point")]))
    called = []
    new, recs = ca.decide_and_apply(
        ARTICLE, ca.parse_sheet(sh),
        generate=lambda p: called.append(p) or "x")
    assert recs[0]["status"] == "skipped-split-panel", recs
    assert not called
    assert q in new
    print("  split_panel_skipped: ok")


def test_constitution_declined():
    q = "The bridge sentence carries the constitution and must never change."
    sh = sheet(conv(q, [("levine", "CUT", "flat"),
                        ("didion", "CUT", "flat")]))
    new, recs = ca.decide_and_apply(
        ARTICLE, ca.parse_sheet(sh),
        protected=["The bridge sentence carries the constitution"])
    assert recs[0]["status"] == "declined-constitution", recs
    assert "cause" in recs[0]
    assert q in new
    print("  constitution_declined: ok")


def test_remedy_conflict_prefers_omission():
    q = ("Trying to size a business that does not exist reveals nothing "
         "about whether it will ever exist.")
    sh = sheet(conv(q, [("didion", "CUT", "circles its own terms"),
                        ("levine", "Sizing a phantom proves nothing.",
                         "shorter")]))
    called = []
    new, recs = ca.decide_and_apply(
        ARTICLE, ca.parse_sheet(sh),
        generate=lambda p: called.append(p) or "x")
    assert recs[0]["status"] == "applied-deletion", recs
    assert not called, "deletion must author no prose and call no model"
    assert q not in new
    print("  remedy_conflict_prefers_omission: ok")


def test_gate_rejection():
    q = ("The follow-up sentence restates what the price already showed.")
    sh = sheet(conv(q, [("levine", "Trim.", "trim"),
                        ("didion", "Trim.", "trim")]))
    # candidate drops the number and the citation -> gate keeps original
    new, recs = ca.decide_and_apply(
        ARTICLE, ca.parse_sheet(sh),
        generate=lambda p: "The price is stated once and that is that.")
    assert recs[0]["status"] == "kept-gate", recs
    assert "number multiset" in recs[0]["cause"]
    assert q in new
    print("  gate_rejection: ok")


def test_cross_instrument_deletion():
    q = "The second paragraph stands alone and says one plain thing."
    single = '### levine\n\n1. "%s" → CUT — *adds nothing*\n' % q
    targets = ca.parse_sheet(sheet(single_blocks=single))
    # not convergent, no cheap rank -> skipped
    new, recs = ca.decide_and_apply(ARTICLE, targets)
    assert recs[0]["status"] == "skipped-not-convergent", recs
    # ranked cheap by reverse-outline -> accepted as a deletion
    new, recs = ca.decide_and_apply(ARTICLE, targets, cheap={2})
    assert recs[0]["status"] == "applied-deletion", recs
    assert recs[0]["cross_instrument"] == "reverse-outline-cheap"
    assert q not in new
    print("  cross_instrument_deletion: ok")


def test_deletion_only_replacement():
    q = ("Trying to size a business that does not exist reveals nothing "
         "about whether it will ever exist.")
    trimmed = "Trying to size a business that does not exist reveals nothing."
    calls = []

    def must_not_run(prompt):
        calls.append(prompt)
        return "x"

    sh = sheet(conv(q, [("iceberg-a", trimmed, "warrant tail"),
                        ("iceberg-b", trimmed, "reader infers it")]))
    new, recs = ca.decide_and_apply(ARTICLE, ca.parse_sheet(sh),
                                    generate=must_not_run)
    assert recs[0]["status"] == "applied-deletion", recs
    assert not calls, "a deletion-only replacement must not call the model"
    assert trimmed in new and "ever exist" not in new
    # one added word disqualifies the path: it goes to the transport
    added = "Trying to size a business that does not exist reveals little."
    sh = sheet(conv(q, [("iceberg-a", added, "x"), ("iceberg-b", added, "y")]))
    _new, recs = ca.decide_and_apply(ARTICLE, ca.parse_sheet(sh))
    assert recs[0]["status"] == "kept-no-model", recs
    # a trim that drops a number is gated
    q2 = "The system costs 42 dollars per run and the price is stated once [3]."
    t2 = "The system costs dollars per run and the price is stated once [3]."
    sh = sheet(conv(q2, [("iceberg-a", t2, "x"), ("iceberg-b", t2, "y")]))
    _new, recs = ca.decide_and_apply(ARTICLE, ca.parse_sheet(sh))
    assert recs[0]["status"] == "kept-gate", recs
    print("  deletion_only_replacement: ok")


def test_counts():
    q = ("Trying to size a business that does not exist reveals nothing "
         "about whether it will ever exist.")
    sh = sheet(conv(q, [("a", "CUT", "x"), ("b", "CUT", "y")]))
    _new, recs = ca.decide_and_apply(ARTICLE, ca.parse_sheet(sh))
    c = ca.counts(recs)
    assert c["applied"] == 1 and c["kept"] == 0 and c["declined_by_rule"] == 0
    print("  counts: ok")


# --- GH-430: every target in a paragraph applies, paragraphs in parallel ---

CHAIN = """# Title

The gateway forwards each request to the model it names and returns the reply unchanged. It also writes the latency to a log that nobody reads. The billing stays on the provider side.

The shim translates the request into the native format. The operators read its dashboard daily.

The third paragraph has a closing sentence that restates the point. It stands.
"""

S1 = "The gateway forwards each request to the model it names and returns the reply unchanged."
S2 = "It also writes the latency to a log that nobody reads."
S3 = "The billing stays on the provider side."


def _rewriter(table):
    """generate stub: replace the quoted sentence per table, keep the rest."""
    def gen(prompt):
        quote = prompt.split('Sentence to change: "', 1)[1].split('"\n', 1)[0]
        par = prompt.split("Paragraph:\n", 1)[1]
        return par.replace(quote, table[quote])
    return gen


def test_two_rewrites_in_one_paragraph_both_apply():
    sh = sheet(conv(S1, [("a", "Shorter.", "x"), ("b", "Shorter.", "y")]) +
               conv(S3, [("a", "Plainer.", "x"), ("b", "Plainer.", "y")]))
    gen = _rewriter({S1: "The gateway passes each request to its model.",
                     S3: "Billing stays with the provider."})
    new, recs = ca.decide_and_apply(CHAIN, ca.parse_sheet(sh), generate=gen)
    assert [r["status"] for r in recs] == ["applied-rewrite"] * 2, recs
    assert "passes each request to its model." in new
    assert "Billing stays with the provider." in new
    assert not any(r["status"] == "kept-paragraph-already-edited" for r in recs)
    print("  two_rewrites_in_one_paragraph_both_apply: ok")


def test_deletion_and_rewrite_in_one_paragraph():
    sh = sheet(conv(S2, [("a", "CUT", "x"), ("b", "CUT", "y")]) +
               conv(S1, [("a", "Shorter.", "x"), ("b", "Shorter.", "y")]))
    gen = _rewriter({S1: "The gateway passes each request to its model."})
    new, recs = ca.decide_and_apply(CHAIN, ca.parse_sheet(sh), generate=gen)
    assert {r["status"] for r in recs} == {"applied-deletion", "applied-rewrite"}, recs
    assert S2 not in new and "passes each request to its model." in new
    print("  deletion_and_rewrite_in_one_paragraph: ok")


def test_quote_consumed_by_an_earlier_edit():
    sh = sheet(conv(S1, [("a", "Merge.", "x"), ("b", "Merge.", "y")]) +
               conv(S2, [("a", "Plainer.", "x"), ("b", "Plainer.", "y")]))
    gen = _rewriter({S1: "The gateway forwards each request to its model, returns the reply unchanged, and logs the latency."})
    # the first rewrite leaves S2 in place; make it absorb S2 instead
    def absorbing(prompt):
        out = gen(prompt)
        return out.replace(" " + S2, "")
    new, recs = ca.decide_and_apply(CHAIN, ca.parse_sheet(sh), generate=absorbing)
    assert recs[0]["status"] == "applied-rewrite", recs
    assert recs[1]["status"] == "kept-quote-gone-after-edit", recs
    print("  quote_consumed_by_an_earlier_edit: ok")


def test_chain_drift_rolls_back_to_a_fitting_prefix():
    """Each step stays inside 1.35x of its input; together they do not."""
    long1 = S1[:-1] + " and keeps the original headers intact on the way back."
    long3 = S3[:-1] + " under the contract the operator signed with them last year."
    sh = sheet(conv(S1, [("a", "Expand.", "x"), ("b", "Expand.", "y")]) +
               conv(S3, [("a", "Expand.", "x"), ("b", "Expand.", "y")]))
    gen = _rewriter({S1: long1, S3: long3})
    orig = ca.strip_rst(ca.md_paragraphs.parse(CHAIN).paragraphs[0][2])[0]
    step1 = orig.replace(S1, long1)
    assert ca.gate(orig, step1)[0], "fixture: step 1 alone must fit"
    assert not ca.gate(orig, step1.replace(S3, long3))[0], "fixture: chain must not"
    new, recs = ca.decide_and_apply(CHAIN, ca.parse_sheet(sh), generate=gen)
    assert recs[0]["status"] == "applied-rewrite", recs
    assert recs[1]["status"] == "kept-chain-drift", recs
    assert long1 in new and long3 not in new
    print("  chain_drift_rolls_back_to_a_fitting_prefix: ok")


def test_jobs_do_not_change_the_output():
    s4 = "The shim translates the request into the native format."
    s5 = "The third paragraph has a closing sentence that restates the point."
    sh = sheet(conv(S1, [("a", "Shorter.", "x"), ("b", "Shorter.", "y")]) +
               conv(s4, [("a", "Plainer.", "x"), ("b", "Plainer.", "y")]) +
               conv(s5, [("a", "CUT", "x"), ("b", "CUT", "y")]) +
               conv(S3, [("a", "Plainer.", "x"), ("b", "Plainer.", "y")]))
    gen = _rewriter({S1: "The gateway passes each request to its model.",
                     s4: "The shim rewrites the request natively.",
                     S3: "Billing stays with the provider."})
    a_new, a_recs = ca.decide_and_apply(CHAIN, ca.parse_sheet(sh), generate=gen, jobs=1)
    b_new, b_recs = ca.decide_and_apply(CHAIN, ca.parse_sheet(sh), generate=gen, jobs=4)
    assert a_new == b_new
    assert [r["status"] for r in a_recs] == [r["status"] for r in b_recs]
    assert ca.counts(a_recs)["applied"] == 4, a_recs
    print("  jobs_do_not_change_the_output: ok")


if __name__ == "__main__":
    test_convergent_applied_and_marker_roundtrip()
    test_split_panel_skipped()
    test_constitution_declined()
    test_remedy_conflict_prefers_omission()
    test_gate_rejection()
    test_deletion_only_replacement()
    test_cross_instrument_deletion()
    test_counts()
    test_two_rewrites_in_one_paragraph_both_apply()
    test_deletion_and_rewrite_in_one_paragraph()
    test_quote_consumed_by_an_earlier_edit()
    test_chain_drift_rolls_back_to_a_fitting_prefix()
    test_jobs_do_not_change_the_output()
    print("all critic-apply tests passed")
