<!-- Copyright (c) 2026 Petar Djukic. All rights reserved. SPDX-License-Identifier: MIT -->
---
name: critic-apply
description: >-
  Rule-based application of a converged critic sheet: accept every
  convergent target (2+ critics), skip split panels, decline
  constitution-protected spans with cause, prefer the omission when
  remedies conflict, and count reverse-outline cheap ranks as
  convergence for single-critic deletions. Rewrites route through the
  rewrite transport with a narrow one-sentence instruction and a
  mechanical gate (numbers, citations, em-dash/colon budgets, size
  band); deletions apply directly; rst markers round-trip. Reports
  applied/kept/declined-by-rule for the generation: block. Triggers:
  critic apply, apply the critic sheet, apply the panel, apply
  suggestions by rule, converged sheet application.
argument-hint: '--article <draft.md> --sheet <stem>.critic-sheet.md'
---

# Critic Apply (rule-based sheet application)

critic-panel produces the sheet and never applies anything; the author
used to pick by hand, and the auto-application policy (operator,
2026-09-01) ran twice as throwaway scratchpad scripts. This skill is
that policy as versioned code: the author never reads drivel because the
rules decide, and the rules are arguable because they are deterministic.

## The rules

| rule | effect |
|---|---|
| convergent target (2+ distinct critics on one passage) | accepted |
| split panel (a proposal beside a KEEP/NO CHANGE dissent) | skipped — proposal + dissent is not convergence |
| constitution-protected span (`--protected` verbatim spans) | declined with cause, however many critics want it — the constitution outranks the panel |
| remedy conflict inside a convergence, one remedy a CUT | the omission wins — a deletion authors no prose |
| single-critic CUT on a paragraph reverse-outline ranked cheap (`--cheap-paragraphs`) | accepted — cross-instrument agreement counts as convergence for deletions |
| replacement that only removes words (its words a subsequence of the original's, case and punctuation aside) | applied directly, no model call, under the number and citation gate; conflicting trims keep the most text |
| any other single-critic finding | skipped; the author picks those by hand |

## The mechanics (learned the hard way)

- **rst markers are stripped before the model call and reattached
  after** — their digits fail the number gate (measured on the first
  automated run). A deleted paragraph takes its marker line with it.
- **One narrow instruction per rewrite target**, built from the
  critics' *why*, sent through the rewrite transport
  (`CRITIC_APPLY_MODEL`, default `cohere:command-a-03-2025`) — persona
  prose is never spliced; it is guidance at most.
- **The gate**: number multiset (citations masked first), citation
  multiset (`[@key]` and `[n]`), em-dash and colon counts capped at the
  original's, candidate length within 0.5–1.35× of the original, and no
  editorial rationale: critic or pipeline vocabulary the original did not
  use ("gloss", "participle", "the reader", "this sentence", "cold review",
  "the SRD", "spelling conventions"), GH-440 and GH-453. One run replaced
  claims with "The gloss tells a modelling reader who TM Forum is...",
  another wrote "(cold review rejected its deletion)". Copying the
  instruction is not refused by itself: a verdict critic's Fix often holds
  the gloss to insert, and refusing the copy left undefined terms open. A
  gated rejection keeps the original, recorded with its reason.
- **Deletions apply directly** with mechanical punctuation
  normalization; omission is not authorship.
- **Every accepted target in a paragraph applies**, in document order,
  each to the text the previous one left, with the gate run on each step
  (GH-430). One edit per paragraph per pass used to leave most targets
  unapplied: 22 of 23 in one Loom round, the same ones every round. A
  target whose quote an earlier edit consumed is recorded
  `kept-quote-gone-after-edit`; one after its paragraph was cut,
  `kept-paragraph-deleted`. Length does not compose step by step, so a
  chain without a cut is checked against the original paragraph at the
  end and rolled back to its longest prefix inside the 0.5–1.35× band,
  the dropped steps recorded `kept-chain-drift`.
- **A deletion that leans on a kept rewrite is kept too** (GH-441). The
  sheet carries no finding ids, so the link is read off the text: when
  most of a cut sentence's content words appear in the proposed
  replacement of a rewrite the gate kept, the cut was made because the
  rewrite would carry that content, and applying it alone loses it. Such a
  cut is recorded `kept-gate` with the rewrite named as the cause, and the
  paragraph's chain is re-run without it (model answers are cached, so
  only prompts whose paragraph text changed are asked again).
- **Paragraphs run concurrently** (`--jobs`, default 4; 1 is sequential).
  Each model call still carries one paragraph and one sentence, and the
  output does not depend on `--jobs`.

## Usage

```bash
python3 <skill>/scripts/critic_apply.py \
  --article draft.md --sheet draft.critic-sheet.md \
  [--protected constitution-spans.txt] \
  [--cheap-paragraphs 3,7] \
  [--jobs 4] [--dry-run]
```

Output: `<stem>.applied.md` plus `<out>.critic-apply.json` — per-target
records and the applied/kept/declined-by-rule summary the `generation:`
block wants. `--dry-run` decides and reports with no model calls and no
writes. Offline tests: `scripts/test_critic_apply.py`.

## Position

Caller's review phase (GH-208), directly after critic-panel's merge:
sheet → critic-apply → the applied text re-enters the humanize chain as
a new cycle (applied targets are unlaundered rewrite-transport prose).
cold-review and voice-critic read the result; this skill never runs
after the terminal stage of the same cycle.
