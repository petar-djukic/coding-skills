// Copyright (c) 2026 Petar Djukic. All rights reserved. SPDX-License-Identifier: MIT
export const meta = {
  name: 'polish-prose',
  description: 'Polish one prose file: humanize it, then loop critics, rule-based fixes and cold review until a panel read of the final text changes nothing',
  whenToUse: 'Improve, polish, tighten or make better any prose a person reads end to end (essay, post, paper section, README, chapter): the humanize chain once, then reverse-outline, length pre-check, a critic panel answering the focus brief, critic-apply, cold review, ross read and voice-critic, re-reading until the text stops changing',
  phases: [
    { title: 'Preflight', detail: 'worktree branch, skill paths, focus file, baseline commit' },
    { title: 'Humanize', detail: 'the humanize chain, once' },
    { title: 'Review', detail: 'outline, length, panel, apply, cold review, ross, voice-critic; repeats while prose changes' },
    { title: 'Final read', detail: 'read-only panel on the shipping text when the round cap stopped the loop' },
    { title: 'Record', detail: 'generation note, sidecar sweep, report' },
  ],
}

const A = args || {}
const ART = A.article || A.file
if (!ART) throw new Error('polish-prose: args.article (path to the markdown file) is required')
const SK = A.skills_dir || '.agents/skills'
const MAX = A.max_rounds || 3
const ROSS_FIX_ROUNDS = 2
const STEM = ART.replace(/\.md$/, '')
const DEFAULT_ROSTER = ['Levine', 'Didion', 'Hemingway']
// Uploads are opt-in per run (GH-437). The standing consent grant lets the
// humanize drivers score every stage by default, and a run that forgot
// --venue uploaded an unpublished journal section about eight times. A run
// uploads only when the caller passes pangram: true.
const PANGRAM = A.pangram === true
const NO_UPLOAD = `No Pangram uploads in this run: the caller did not opt in (args.pangram). Run every command with PANGRAM_CONSENT=off in its environment, which the writing-voice rule makes win over a standing grant, and pass --no-pangram to every driver that accepts it. Record every Pangram score as "not measured". Where the skill's stop-at-the-upturn rule needs a score to stop on, run one pass and stop.`
const REQUIRED_SKILLS = ['humanize', 'reverse-outline', 'critic-panel', 'critic-apply', 'cold-review', 'voice-critic']

const NO_PROSE = 'You never write article prose yourself. Text changes only through the owning skill: rewrites go through the rewrite transport, deletions and verbatim reverts apply mechanically.'
// Every stage ends in a commit on the worktree branch (GH-434), so the
// history shows what each step did, not only what landed. A stage that
// leaves the article unchanged commits empty, with its result in the body.
const COMMIT = (subject) => `Then commit, whatever happened. If ${ART} changed, git add only ${ART} and commit it as "${subject}". If it did not change, run git commit --allow-empty with the subject "${subject}, no change". Either way the commit body (at most 20 lines) records what this stage found or decided: counts, verdicts, and one line per item it reports. Never commit sidecars.`
const HYGIENE = `Before you return, delete every sidecar this stage created or consumed (reading copies, critic reports, sheets, *.applied.md, JSON reports), and only files whose names start with ${STEM}. The article file is the only file you may leave changed.`

const PREFLIGHT = {
  type: 'object',
  properties: {
    ok: { type: 'boolean' },
    reason: { type: 'string' },
    branch: { type: 'string' },
    missing: { type: 'array', items: { type: 'string' } },
    focus_file: { type: 'string' },
    focus_items: { type: 'array', items: { type: 'string' } },
    precheck_command: { type: 'string' },
    form: { type: 'string' },
    protected_spans: { type: 'array', items: { type: 'string' } },
    roster_name: { type: 'string' },
    roster: { type: 'array', items: { type: 'string' } },
    draft_rules: { type: 'array', items: { type: 'string' } },
    has_front_matter: { type: 'boolean' },
    has_voice_corpus: { type: 'boolean' },
    has_voice_constitution: { type: 'boolean' },
    baseline_sha: { type: 'string' },
    venue: { type: 'string' },
    voice_form: { type: 'string' },
    voice_model: { type: 'string' },
    voice_skip: { type: 'string' },
  },
  required: ['ok', 'reason', 'branch', 'missing', 'focus_file', 'focus_items', 'precheck_command', 'form', 'protected_spans',
    'roster_name', 'roster', 'draft_rules', 'has_front_matter', 'has_voice_corpus', 'has_voice_constitution', 'baseline_sha',
    'voice_form', 'voice_model', 'voice_skip', 'venue'],
}

const HUMANIZE = {
  type: 'object',
  properties: {
    ran: { type: 'boolean' },
    seed_reach: { type: 'string' },
    stages: { type: 'array', items: { type: 'object', properties: { stage: { type: 'string' }, score: { type: 'string' } }, required: ['stage', 'score'] } },
    notes: { type: 'string' },
  },
  required: ['ran', 'seed_reach', 'stages', 'notes'],
}

const OUTLINE = {
  type: 'object',
  properties: {
    round_start_sha: { type: 'string' },
    cheap_paragraphs: { type: 'array', items: { type: 'integer' } },
    split_paragraphs: { type: 'array', items: { type: 'integer' } },
    eroded: { type: 'array', items: { type: 'string' } },
    copy_path: { type: 'string' },
    total_words: { type: 'integer' },
    flagged_paragraphs: { type: 'array', items: { type: 'string' } },
  },
  required: ['round_start_sha', 'cheap_paragraphs', 'split_paragraphs', 'eroded', 'copy_path', 'total_words', 'flagged_paragraphs'],
}

const SHEET = {
  type: 'object',
  properties: {
    sheet_path: { type: 'string' },
    convergent: { type: 'array', items: { type: 'object', properties: { passage: { type: 'string' }, why: { type: 'string' }, critics: { type: 'integer' } }, required: ['passage', 'why', 'critics'] } },
    paragraph_moves: { type: 'array', items: { type: 'string' } },
    classes: { type: 'array', items: { type: 'string' } },
    focus_answers: { type: 'array', items: { type: 'string' } },
    residue_answers: { type: 'array', items: { type: 'string' } },
    single_critic: { type: 'integer' },
  },
  required: ['sheet_path', 'convergent', 'paragraph_moves', 'classes', 'focus_answers', 'residue_answers', 'single_critic'],
}

const APPLY = {
  type: 'object',
  properties: {
    candidate_path: { type: 'string' },
    applied: { type: 'integer' },
    kept: { type: 'integer' },
    declined: { type: 'integer' },
    unapplied_convergent: { type: 'array', items: { type: 'string' } },
    applied_targets: { type: 'array', items: { type: 'string' } },
    applied_quotes: {
      type: 'array',
      items: { type: 'object', properties: { quote: { type: 'string' }, kind: { type: 'string', enum: ['deletion', 'rewrite'] }, paragraph: { type: 'integer' } }, required: ['quote', 'kind', 'paragraph'] },
    },
    committed_sha: { type: 'string' },
  },
  required: ['candidate_path', 'applied', 'kept', 'declined', 'unapplied_convergent', 'applied_targets', 'applied_quotes', 'committed_sha'],
}

const COLD = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['ship as-is', 'ship with reverts', 'reject candidate'] },
    reverts: { type: 'array', items: { type: 'string' } },
    reverted_paragraphs: { type: 'array', items: { type: 'integer' } },
    committed_sha: { type: 'string' },
  },
  required: ['verdict', 'reverts', 'reverted_paragraphs', 'committed_sha'],
}

const ROSS = {
  type: 'object',
  properties: {
    legs: { type: 'array', items: { type: 'string' } },
    convergent: { type: 'array', items: { type: 'string' } },
    reserved: { type: 'array', items: { type: 'string' } },
    sheet_path: { type: 'string' },
  },
  required: ['legs', 'convergent', 'reserved', 'sheet_path'],
}

const VOICE = {
  type: 'object',
  properties: {
    failed: { type: 'array', items: { type: 'string' } },
    flags: { type: 'array', items: { type: 'string' } },
  },
  required: ['failed', 'flags'],
}

const STEP6 = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['clean', 'flagged'] },
    findings: { type: 'array', items: { type: 'string' } },
  },
  required: ['verdict', 'findings'],
}

const DIFF = {
  type: 'object',
  properties: {
    prose_changed: { type: 'boolean' },
    changed_lines: { type: 'integer' },
  },
  required: ['prose_changed', 'changed_lines'],
}

const RECORD = {
  type: 'object',
  properties: {
    committed_sha: { type: 'string' },
    sidecars_left: { type: 'array', items: { type: 'string' } },
  },
  required: ['committed_sha', 'sidecars_left'],
}

const list = (xs) => (xs && xs.length ? xs.map((x) => `- ${x}`).join('\n') : '(none)')

// ---------------------------------------------------------------- Preflight
phase('Preflight')
const pre = await agent(`Preflight for a polish-prose run on ${ART}. The file can be any prose a person reads end to end: an essay, post, paper section, README, or book chapter. ${A.validate_only ? 'VALIDATE ONLY: change nothing, commit nothing.' : ''}

1. Report the current git branch. ${A.validate_only ? 'This is a validate-only run, so any branch is acceptable.' : 'If it is main or master, set ok=false: this pipeline commits, and changes land only on worktree branches (loop workflow).'}
2. Check that ${ART} exists and that each of these skill files exists: ${REQUIRED_SKILLS.map((s) => `${SK}/${s}/SKILL.md`).join(', ')}. List any missing path in "missing" and set ok=false if any are missing.
3. Focus file: ${A.focus_file ? `use ${A.focus_file}.` : `walk up from the article's directory to the repository root looking for critic-focus.md; use the nearest one.`} If found, return its path, each named check as one string in focus_items (verbatim, one per check), and the deterministic pre-check command it names in precheck_command with {article} left as a placeholder. If none exists, return empty values: the panel then reads without a focus list, which is allowed.
4. Form: read the file to decide its form (how-to, essay, polemic, post, paper section, README, chapter, or the name of a constitution under .agents/constitutions/ that matches). ${A.form ? `The caller says the form is ${A.form}; use that.` : ''} If a constitution file exists for the form, return in protected_spans every span it requires that appears verbatim in the file (for a how-to: the bridge sentence, the learning-objectives paragraph, the "The steps" transition), quoted exactly. If a required span is missing from the file, say so in reason.
5. Roster: read the roster table in ${SK}/critic-panel/references/personas.md. ${A.roster ? `The caller asks for roster ${JSON.stringify(A.roster)}; use it (a roster name or a list of persona names).` : 'Use "book" for a book chapter, "article" for everything else.'} Return roster_name and the persona names in roster order.
6. The draft's own rules: per the "The draft's own rules" section of ${SK}/critic-panel/SKILL.md, list every rules file found beside or above the file (docs/constitutions/voice.yaml, docs/constitutions/argument.yaml, the chapter's SRD under docs/srd/, or a matching constitution under .agents/constitutions/) in draft_rules.
7. Optional stages: has_front_matter = the file starts with a YAML front-matter block; has_voice_corpus = a writing-voice/ directory with exemplars is found walking up from the file (humanize needs it); has_voice_constitution = writing-voice/voice-constitution.md is found the same way (voice-critic needs it).
8. voice-critic readiness, once for the whole run: if has_voice_constitution, run ${SK}/voice-critic/scripts/voice_critic.py --preflight --form "<the form from step 4>" (in the skills' pixi environment, as ${SK}/voice-critic/SKILL.md says) and copy its JSON fields: voice_form = "form", voice_model = "model", voice_skip = "skip" (empty string for any null). Do not retry it with another form or model, and do not pull a model: a skip is a finding, reported once. If has_voice_constitution is false, return all three as empty strings.
9. Venue: ${A.venue ? `the caller says ${A.venue}; return it.` : `look for writing-voice/venues/*.yaml walking up from the file. If profiles exist, return the name of the one whose description fits the form from step 4 (a paper section is academic, a book chapter is book, a newsletter post is newsletter, a how-to or technical essay is technical-essay, an industry report or whitepaper is industry-report); return an empty string when none fits or there are no profiles. Do not guess past the descriptions.`}
10. ${A.validate_only ? 'Do not commit. Return baseline_sha as the current HEAD.' : `If ${ART} has uncommitted changes, commit them alone as "draft: <slug> (pre-pipeline baseline)". Return baseline_sha as HEAD after that.`}`,
  { label: 'preflight', schema: PREFLIGHT, effort: 'low' })

if (!pre || !pre.ok) {
  return { status: 'refused', reason: pre ? pre.reason : 'preflight agent failed', preflight: pre }
}
const CRITICS = pre.roster && pre.roster.length ? pre.roster : DEFAULT_ROSTER
const VENUE = A.venue || pre.venue || ''
const skipped = []
if (!pre.has_voice_corpus) skipped.push('humanize (no writing-voice/ corpus found)')
if (!pre.has_voice_constitution) skipped.push('voice-critic (no voice constitution found)')
else if (pre.voice_skip || !pre.voice_form || !pre.voice_model) skipped.push(`voice-critic (${pre.voice_skip || 'preflight returned no form or judge'})`)
const VOICE_READY = pre.has_voice_constitution && !pre.voice_skip && pre.voice_form && pre.voice_model
if (!pre.has_front_matter) skipped.push('generation note (no front matter; the report is the record)')
log(`branch ${pre.branch}; form ${pre.form || 'unknown'}; venue ${VENUE || 'none'}; pangram ${PANGRAM ? 'opted in' : 'off'}; roster ${pre.roster_name || 'article'} (${CRITICS.join(', ')}); focus file ${pre.focus_file || 'none (generic read)'}; ${pre.protected_spans.length} protected spans${skipped.length ? `; skipping: ${skipped.join('; ')}` : ''}`)
if (A.validate_only) {
  return { status: 'validated', roster: CRITICS, venue: VENUE || null, pangram: PANGRAM, skipped, preflight: pre }
}

// ---------------------------------------------------------------- Humanize
phase('Humanize')
let hum = { ran: false, seed_reach: 'skipped', stages: [], notes: A.skip_humanize ? 'skip_humanize set by caller' : 'no writing-voice/ corpus found; humanize needs its exemplars' }
if (!A.skip_humanize && pre.has_voice_corpus) {
  hum = await agent(`Run the humanize skill on ${ART}: read ${SK}/humanize/SKILL.md and follow it end to end, exactly as written, including its stage order, its measurements, and its report. ${VENUE ? `Use venue mode with --venue ${VENUE}.` : ''}
${PANGRAM ? '' : NO_UPLOAD}

Commit each stage's output as it lands, one commit per stage, with the stage name in the subject ("filter-tells: <slug>", "match-voice: <slug>", "tighten: <slug>", ...). Do not squash.
filter-tells Step 6 (the independent evaluator) is not yours to run: this workflow runs it after you, as its own agent in a fresh context, because the context that made the rewrites cannot be the one that judges them. Skip it, and say in your report that it was handed off.
Respect locked spans and these protected spans verbatim:
${list(pre.protected_spans)}
If a model call fails on TLS certificates, point SSL_CERT_FILE at certifi's bundle; read API keys only through the repository's secrets convention and never print them.
${NO_PROSE}
${HYGIENE}
Return seed reach exactly as the skill reports it, each stage with its score, and anything the caller must know.`,
    { label: 'humanize', schema: HUMANIZE })
  if (!hum) return { status: 'failed', stage: 'humanize', preflight: pre }
  log(`humanize: seed reach ${hum.seed_reach}`)
}

// filter-tells Step 6 in a fresh context (GH-443). Run inside the humanize
// agent it had no subagent tool, so the triage was done by the context that
// made the rewrites, the maker-checker gap Step 6 exists to close.
let step6 = { verdict: 'skipped', findings: [], reason: hum.ran ? '' : 'humanize did not run' }
if (hum.ran) {
  step6 = await agent(`You are filter-tells' Step 6 independent evaluator for ${ART}, in a fresh context. Read "### Step 6: Final Semantic Verification (independent evaluator)" in ${SK}/filter-tells/SKILL.md and follow it.

You see only the final text: ${ART} as it stands now. You have not seen the rewrite history, the reasoning, or the diffs, and you must not look: do not read git log, git diff, earlier commits, or any sidecar. For the Step 3 report, run filter-tells' own lexical and structural scans (${SK}/filter-tells/scripts/detect-lexical.sh and detect-structural.py) on ${ART} yourself.

Take the stance Step 6 gives you: assume the rewrites introduced new patterns, and find them. Return verdict "clean" only if you find none; otherwise "flagged", with each finding as one line: the quoted span, the pattern, and what would fix it. Change nothing in ${ART}. ${COMMIT('filter-tells step 6: <slug> (independent evaluator)')} The body carries the verdict and one line per finding. ${HYGIENE}`,
    { label: 'filter-tells step 6', phase: 'Humanize', schema: STEP6, effort: 'medium' })
  if (!step6) step6 = { verdict: 'failed', findings: [], reason: 'the evaluator agent failed' }
  log(`filter-tells step 6 (fresh context): ${step6.verdict}, ${step6.findings.length} finding(s)`)
}

// ---------------------------------------------------------------- Review
const focusBlock = pre.focus_items.length
  ? `FOCUS LIST. Answer every item explicitly, BY NAME, inside your ## Diagnosis, before your free read:\n${list(pre.focus_items)}`
  : 'No focus list was supplied for this repository: give your free read.'

async function panel(o, residue, rejected, round, tag) {
  const criticReports = await parallel(CRITICS.map((name) => () => agent(`You are the ${name} critic on a critic-panel Mode A read. Fresh context by design: you have not seen any other critic's report and must not look for one.

Read your persona brief (the ${name} entry) in ${SK}/critic-panel/references/personas.md; it states your kind (suggest or verdict). From ${SK}/critic-panel/SKILL.md read "The two report formats" (use your kind's format with its literal headings) and "Constraints" (the shared ones and your kind's). Then read the reading copy at ${o.copy_path}.
${pre.draft_rules.length ? `Judge against the draft's own rules, which outrank a generic standard:\n${list(pre.draft_rules)}` : ''}

${residue.length
    ? `${pre.focus_items.length ? focusBlock : 'FOCUS LIST. Answer every item explicitly, BY NAME, inside your ## Diagnosis, before your free read:'}
Open items carried from earlier stages, part of the focus list (GH-457). Answer each one BY NUMBER and NAME in your Diagnosis: still present, fixed, or not a defect, with the reason:
${residue.map((r, i) => `R${i + 1}. ${r}`).join('\n')}`
    : focusBlock}

Measured length: ${o.total_words} prose words. Paragraphs over the paragraph budget:
${list(o.flagged_paragraphs)}


${rejected.length ? `Closed: cold review rejected these edits in earlier rounds. Do not propose them again, in any wording. If the passage still needs work, propose a different change and say in its Buys line how it avoids the rejected one:\n${list(rejected)}` : ''}

Write your report to ${STEM}.critic-${name.toLowerCase()}.md and return only the word done.`,
    { label: `${tag} r${round}: ${name}`, phase: tag === 'final' ? 'Final read' : 'Review' })))
  if (criticReports.filter(Boolean).length < CRITICS.length) {
    log(`round ${round}: ${CRITICS.length - criticReports.filter(Boolean).length} critic(s) failed; merging what returned`)
  }
  return agent(`Merge the critic-panel reports for ${ART}: ${CRITICS.map((n) => `${STEM}.critic-${n.toLowerCase()}.md`).join(', ')} (skip any that does not exist).

Run ${SK}/critic-panel/scripts/converge.py on them with --out ${STEM}.critic-sheet.md --roster ${CRITICS.map((n) => n.toLowerCase()).join(',')}. If a report is refused as unparseable, fix only its headings and field labels to the literal format in ${SK}/critic-panel/SKILL.md (never its content) and re-run.

From the sheet and the reports return: every convergent passage (2+ critics) with its first words, the shared reason, and the critic count; the paragraph moves; the declared defect classes; the consensus answer to each focus-list item from the Diagnoses (one line each); one line per open item R1, R2, ... in residue_answers, giving its number, the consensus (still present, fixed, not a defect) and how many critics answered it, with "unanswered" when none did; and the single-critic suggestion count. Keep the critic reports and sheet on disk (the next stage reads the sheet) and return its path.
${COMMIT(tag === 'final' ? 'panel: <slug> (final read)' : `panel: <slug> (round ${round})`)} The body carries the convergent count, one line per convergent passage (first words and reason), one line per focus-list answer, and one line per open-item answer.`,
    { label: `${tag} r${round}: converge`, phase: tag === 'final' ? 'Final read' : 'Review', schema: SHEET, effort: 'low' })
}

// Cold review of a candidate against the article as committed at baseline.
// critic-apply's output and the Iceberg pass's both go through it, so a
// deletion that leaves a fragment or drops a statement id is reverted
// instead of committed (GH-416).
function coldReview(candidateSha, round, stage, label) {
  return agent(`Cold review, fresh context. You have not seen how the candidate was produced and must not ask.

Read ${SK}/cold-review/SKILL.md and its prompt template ${SK}/cold-review/references/review-prompt.md. Baseline: ${ART} as committed at ${candidateSha}^ (the commit before the candidate; extract it with git show to a temporary file). Candidate: ${ART} as committed at ${candidateSha}, which is the working file now. Run the skill's screen, review paragraph by paragraph as the template specifies, and decide with its closed vocabulary.

- ship as-is: leave ${ART} as it is.
- ship with reverts: run the skill's apply with your revert list against the baseline and write the result over ${ART}.
- reject candidate: restore ${ART} to the baseline exactly (git show ${candidateSha}^:${ART}).
High-value targets: numbers, citations, quotations, statement ids (R1.2, AC3), sentences left as fragments, and these protected spans:
${list(pre.protected_spans)}
${COMMIT(`cold-review: <slug> (round ${round}, ${stage}: <verdict>)`)} For reverts, one body line per reverted paragraph and why; for a rejection, the reasons. The candidate stays in history at ${candidateSha}, so git show reads what was tried. Return the verdict, each revert as one line, reverted_paragraphs (the 1-based prose paragraph numbers you reverted, as cold_review.py numbers them; for a rejection, every paragraph the candidate changed), and HEAD after your commit. ${HYGIENE}`,
    { label, phase: 'Review', schema: COLD })
}

// What outranks the Iceberg removal test: the caller's focus list, the
// draft's own rules, and this round's panel answers to the focus list.
function keepBlock(focusAnswers) {
  const parts = []
  if (pre.focus_items.length) parts.push(`The caller's focus list:\n${list(pre.focus_items)}`)
  if (pre.draft_rules.length) parts.push(`The draft's own rules (read each file):\n${list(pre.draft_rules)}`)
  if (focusAnswers && focusAnswers.length) parts.push(`The panel's answers to the focus list this round, including the clauses it said to keep:\n${list(focusAnswers)}`)
  return parts.length
    ? `KEEP LIST. These outrank the removal test. A clause a focus item, a rule, or the panel's answers name as carrying the argument (a consequence that states what a feature buys, an SRD-required consequence, a closer with a statement id such as R1.2 or AC3) is not a warrant tail: do not suggest cutting it, whatever its grammar.\n${parts.join('\n\n')}`
    : ''
}

const rounds = []
let residue = (step6.findings || []).map((f) => `filter-tells step 6 (independent evaluator after humanize): ${f}`)
// Cross-family ross findings left unfixed (GH-439). After round 1 ross only
// repairs regressions, so a finding already in the text had no route to a
// fix: in the S2 run the same unglossed terms were reported NOT FIXED in
// every round. They join the residue the next panel must answer by name,
// and the final residue, so the report names them either way.
const rossOpen = (ross, round) => (ross && ross.convergent ? ross.convergent : [])
  .filter((line) => !/^\s*FIXED\s*:/i.test(line))
  .map((line) => `ross round ${round}, convergent across families: ${line.replace(/^\s*NOT FIXED:?\s*/i, '')}`)
let lastRossOpen = []
// Edits cold review rejected, closed for the rest of the run (GH-438). The
// S2 run re-proposed, re-applied and re-reverted the same three edits in
// every round because the next panel never heard about the reverts.
const rejected = []
// The same rejections as data critic-apply enforces (GH-467): the prompt
// above is advice the panel can reword around, and in S6 a rejected deletion
// came back in other words, was applied, and was rejected again.
const closedTargets = []
const closedFlag = () => (closedTargets.length
  ? `Write this JSON list to a temporary file and pass it to critic-apply with --closed (changes cold review already rejected; critic-apply declines the same kind of change on the same passage): ${JSON.stringify(closedTargets)}`
  : '')
const closeRejected = (review, applyResult, round, stage) => {
  if (!review || !applyResult) return
  const lines = review.verdict === 'reject candidate'
    ? (applyResult.applied_targets || [])
    : (review.reverts || [])
  for (const line of lines) rejected.push(`rejected by cold review in round ${round} (${stage}), do not re-propose: ${line}`)
  const reverted = review.verdict === 'reject candidate' ? null : new Set(review.reverted_paragraphs || [])
  if (review.verdict === 'ship as-is') return
  for (const q of applyResult.applied_quotes || []) {
    if (!reverted || reverted.has(q.paragraph)) closedTargets.push({ quote: q.quote, kind: q.kind, round })
  }
}
let stable = false
let lastSheet = null

for (let round = 1; round <= MAX; round++) {
  phase('Review')
  const outline = await agent(`Round ${round} start for ${ART}.

1. reverse-outline: read ${SK}/reverse-outline/SKILL.md. If the article carries no rst: markers, run annotate (session-model labelling, as the skill specifies) and validate; otherwise run audit against the existing markers and check --renumber. Then run rank. ${COMMIT(`reverse-outline: <slug> (round ${round})`)} The body carries the audit result and rank's cheap and split paragraphs.
2. Return round_start_sha = HEAD after that commit, the paragraph numbers rank lists as cheap deletion candidates, the split paragraphs, and any paragraph audit marks eroded or changed.
3. Build the critics' reading copy with ${SK}/critic-panel/scripts/prepare_copy.py and return its path (leave it on disk for the critics).
4. ${pre.precheck_command ? `Run the length pre-check: ${pre.precheck_command.replace('{article}', ART)}. Return the prose word total and each flagged paragraph as one line (line number, word count, first words, over or DEFECT).` : 'No pre-check command was supplied; return total_words as the prose word count and an empty flagged list.'}
${NO_PROSE}`,
    { label: `r${round}: outline + length`, phase: 'Review', schema: OUTLINE, effort: 'low' })
  if (!outline) return { status: 'failed', stage: `round ${round} outline`, rounds }

  const sheet = await panel(outline, residue, rejected, round, 'panel')
  if (!sheet) return { status: 'failed', stage: `round ${round} converge`, rounds }
  lastSheet = sheet

  const applied = await agent(`Apply the converged critic sheet ${sheet.sheet_path} to ${ART} with the critic-apply skill: read ${SK}/critic-apply/SKILL.md and run its script as written.

Pass as protected spans (write them to a temporary spans file):
${list(pre.protected_spans)}
Pass --cheap-paragraphs ${outline.cheap_paragraphs.join(',') || '(none)'} from reverse-outline's rank.
${closedFlag()}
Write the skill's candidate over ${ART}: cold review judges it next, as a commit, so a rejected attempt stays in history. ${COMMIT(`critic-apply: <slug> (round ${round}, candidate)`)} The body carries the applied/kept/declined counts and one line per target not applied, with its status.
Return the article path as candidate_path, the counts, every convergent target that was not applied (first words plus the reason), every target that was applied (first words plus the change, one line each) as applied_targets, every target the log records with an applied- status as applied_quotes (its target_quote, its kind, and its paragraph number) from the skill's .critic-apply.json log, and HEAD after your commit as committed_sha.
Then delete the three critic reports and the sheet. ${NO_PROSE}`,
    { label: `r${round}: critic-apply`, phase: 'Review', schema: APPLY })
  if (!applied) return { status: 'failed', stage: `round ${round} critic-apply`, rounds }

  let cold = { verdict: 'ship as-is', reverts: [], committed_sha: applied.committed_sha }
  if (applied.applied > 0) {
    cold = await coldReview(applied.committed_sha, round, 'critic-apply', `r${round}: cold review`)
    if (!cold) return { status: 'failed', stage: `round ${round} cold review`, rounds, unreviewed_candidate: applied.committed_sha, note: `HEAD carries an unreviewed critic-apply candidate; reset ${ART} to ${applied.committed_sha}^ before using the branch` }
    closeRejected(cold, applied, round, 'critic-apply')
  }

  phase('Review')
  const icebergLegs = await parallel(['a', 'b'].map((leg) => () => agent(`You are the Iceberg critic, leg ${leg}, in a critic-panel read of ${ART}. Fresh context by design: do not look for any other critic's report.

Read your persona brief, the "## Iceberg — The Inference Test" entry in ${SK}/critic-panel/references/personas.md, and "## Category 16: Warrant Tails" in ${SK}/filter-tells/references/cot-leakage-patterns.md; from ${SK}/critic-panel/SKILL.md read "The two report formats" (suggest format, literal headings) and "Constraints". Build your own reading copy of ${ART} as it stands now with ${SK}/critic-panel/scripts/prepare_copy.py, and sweep all of it: return every warrant tail that passes the removal test, with no cap. Replacement is CUT or the quoted span with words removed and none added.
${keepBlock(sheet.focus_answers)}
${rejected.length ? `Closed: cold review rejected these edits in earlier rounds; do not suggest them again:\n${list(rejected)}` : ''}

Write the report to ${STEM}.critic-iceberg-${leg}.md, delete your reading copy, and return only: done, N suggestions.`,
    { label: `r${round}: iceberg ${leg}`, phase: 'Review' })))
  const icebergKeep = keepBlock(sheet.focus_answers)
  const iceberg = await agent(`Apply the Iceberg pass to ${ART}. Merge ${STEM}.critic-iceberg-a.md and ${STEM}.critic-iceberg-b.md with ${SK}/critic-panel/scripts/converge.py --roster iceberg-a,iceberg-b --out ${STEM}.iceberg-sheet.md.
${icebergKeep ? `Before applying, check every convergent cut against the keep list below. A cut that removes a clause the keep list names, or that removes a statement id (R1.2, AC3), is reported, not applied: delete it from the sheet and list it among the unapplied targets with the reason "kept: <the focus item, rule, or panel answer>".
${icebergKeep}
` : ''}Then run the critic-apply skill (${SK}/critic-apply/SKILL.md) on the sheet${closedTargets.length ? ', passing --closed as below,' : ''} with these protected spans:
${list(pre.protected_spans)}
${closedFlag()}
Convergent cuts and deletion-only trims apply directly with no model call; report any target that could not be placed (for example a span inside a list item, which critic-apply does not locate) instead of placing it by hand. Write the skill's candidate over ${ART}: cold review judges it next, as a commit. ${COMMIT(`iceberg: <slug> (round ${round}, candidate)`)} The body carries each leg's suggestion count, the applied/kept/declined counts, and one line per cut not applied, with its reason.
Return the article path as candidate_path, the counts, every convergent target left unapplied (first words plus the reason), every cut that was applied (first words, one line each) as applied_targets, every target the log records with an applied- status as applied_quotes (its target_quote, its kind, and its paragraph number) from the skill's .critic-apply.json log, and HEAD after your commit as committed_sha. ${HYGIENE}`,
    { label: `r${round}: iceberg apply`, phase: 'Review', schema: APPLY, effort: 'low' })
  let icebergCold = null
  if (iceberg && iceberg.applied > 0) {
    icebergCold = await coldReview(iceberg.committed_sha, round, 'iceberg', `r${round}: iceberg cold review`)
    if (!icebergCold) return { status: 'failed', stage: `round ${round} iceberg cold review`, rounds, unreviewed_candidate: iceberg.committed_sha, note: `HEAD carries an unreviewed iceberg candidate; reset ${ART} to ${iceberg.committed_sha}^ before using the branch` }
    closeRejected(icebergCold, iceberg, round, 'iceberg')
  }
  log(`round ${round}: iceberg legs ${icebergLegs.filter(Boolean).length}/2, ${iceberg ? iceberg.applied : 0} warrant tails cut in the candidate, cold review ${icebergCold ? icebergCold.verdict : 'not run'}`)

  const fixRoss = round <= ROSS_FIX_ROUNDS
  const ross = await agent(`ross read (critic-panel Mode C) on ${ART}, round ${round}. Read the Mode C section of ${SK}/critic-panel/SKILL.md and follow its protocol exactly.

Run its session leg yourself from the --copy-only reading copy (forward-only, one sentence of lookback, every inference you had to make counts as a finding), then two cross-family Ollama legs with ${SK}/critic-panel/scripts/ross_read.py --model <name>, choosing two model families different from each other and from yours. Merge with converge.py.

${fixRoss
    ? `${round === 1 ? 'Fix findings convergent ACROSS families on non-reserved prose.' : 'Fix only regressions the previous round introduced that are convergent across families; nothing else.'} Apply them with the critic-apply skill (${SK}/critic-apply/SKILL.md) using the merged ross sheet, with the protected spans below. Before writing it over ${ART}, run ${SK}/cold-review/scripts/cold_review.py screen with the current article as baseline and the fixed text as candidate, and revert (with its apply) every paragraph where a number, citation or quotation drifted. Then write the result over ${ART}.`
    : 'Read only this round: the batch cap (fix convergents in round 1, repair regressions in round 2, then stop) is reached. Change nothing.'}
${COMMIT(`ross: <slug> (round ${round}${fixRoss ? '' : ', read only'})`)} The body carries the legs and one line per cross-family convergent finding, fixed or not.
Reserved, never fixed (report them): single-model findings, locked spans, rule tensions, the protected spans below, and any sentence the article's generation notes record as the author's own hand edit.
Protected spans:
${list(pre.protected_spans)}
Return the legs you ran (model names), every cross-family convergent finding as one line that starts with "FIXED:" or "NOT FIXED:", and the reserved items. ${NO_PROSE} ${HYGIENE}`,
    { label: `r${round}: ross read`, phase: 'Review', schema: ROSS })

  const voice = VOICE_READY
    ? await agent(`voice-critic on ${ART}: read ${SK}/voice-critic/SKILL.md and run its script read-only with --judge --form ${pre.voice_form} --model ${pre.voice_model} --json, exactly these values: preflight resolved them, and a different form or model is not yours to choose. If the run fails, return the failure as one flag; do not retry with other arguments. Return the dimensions that FAIL and each flagged span as one line (dimension, quoted span, line range). Never edit anything. ${COMMIT(`voice-critic: <slug> (round ${round})`)} The body carries each dimension's verdict and the flagged spans. ${HYGIENE}`,
      { label: `r${round}: voice-critic`, phase: 'Review', schema: VOICE, effort: 'low' })
    : { failed: [], flags: [`skipped: ${pre.has_voice_constitution ? (pre.voice_skip || 'preflight returned no form or judge') : 'no voice constitution found'}`] }

  const diff = await agent(`Did round ${round} change the prose of ${ART}? Run git diff ${outline.round_start_sha} -- ${ART} and count added or removed lines, ignoring lines that are only rst: marker comments or whitespace. Return prose_changed and the count.`,
    { label: `r${round}: diff`, phase: 'Review', schema: DIFF, effort: 'low' })

  lastRossOpen = rossOpen(ross, round)
  residue = [...applied.unapplied_convergent, ...sheet.paragraph_moves, ...lastRossOpen]
  rounds.push({
    round,
    words: outline.total_words,
    flagged_paragraphs: outline.flagged_paragraphs.length,
    convergent: sheet.convergent.length,
    focus_answers: sheet.focus_answers,
    residue_answers: sheet.residue_answers,
    classes: sheet.classes,
    applied: applied.applied,
    kept: applied.kept,
    declined: applied.declined,
    cold: cold.verdict,
    reverts: cold.reverts.length,
    iceberg: iceberg ? { applied: iceberg.applied, unapplied: iceberg.unapplied_convergent, cold: icebergCold ? icebergCold.verdict : 'not run', reverts: icebergCold ? icebergCold.reverts.length : 0 } : 'failed',
    ross: ross ? { legs: ross.legs, convergent: ross.convergent, reserved: ross.reserved } : 'failed',
    voice: voice || 'failed',
    prose_changed: diff ? diff.prose_changed : true,
    eroded: outline.eroded,
  })
  log(`round ${round}: ${sheet.convergent.length} convergent, ${applied.applied} applied, cold review ${cold.verdict}, prose ${diff && !diff.prose_changed ? 'unchanged' : 'changed'}`)

  if (diff && !diff.prose_changed) { stable = true; break }
}

// ---------------------------------------------------------------- Final read
let finalRead = null
if (!stable) {
  phase('Final read')
  log(`round cap ${MAX} reached with the text still changing: one read-only panel pass on the shipping text`)
  const o = await agent(`Prepare a read-only final panel read of ${ART}: build the reading copy with ${SK}/critic-panel/scripts/prepare_copy.py and return its path. ${pre.precheck_command ? `Run ${pre.precheck_command.replace('{article}', ART)} and return the total and flagged paragraphs.` : 'Return the prose word count and an empty flagged list.'} Return round_start_sha as HEAD and empty arrays for the reverse-outline fields. Change nothing.`,
    { label: 'final: copy + length', phase: 'Final read', schema: OUTLINE, effort: 'low' })
  if (o) {
    finalRead = await panel(o, residue, rejected, MAX + 1, 'final')
    if (finalRead) residue = [...finalRead.convergent.map((c) => `${c.passage} — ${c.why} (x${c.critics})`), ...finalRead.paragraph_moves, ...lastRossOpen]
  }
}

// ---------------------------------------------------------------- Record
phase('Record')
const record = await agent(`${pre.has_front_matter ? `Record this polish-prose run in ${ART}'s front matter generation: block, following the provenance conventions the repository already uses there (append an entry, or start the block if there is none; never rewrite earlier entries).` : `${ART} has no front matter, so write no generation note: skip straight to the sidecar sweep below, and commit only if a sidecar was tracked.`} The entry names the pipeline (polish-prose), humanize seed reach (${hum.seed_reach}), the number of review rounds (${rounds.length}), whether the loop ended on a stable read (${stable}), per-round applied/kept/declined counts and cold-review verdicts:
${rounds.map((r) => `round ${r.round}: applied ${r.applied}, kept ${r.kept}, declined ${r.declined}, cold ${r.cold}, convergent ${r.convergent}`).join('\n')}
the residue still open:
${list(residue)}
and the edits cold review rejected, closed for the run (${rejected.length}):
${list(rejected)}

Then delete every remaining sidecar whose name starts with ${STEM} other than the article itself (critic copies, reports, sheets, *.applied.md, *.outline.md, JSON reports), list any you could not delete, and commit the file as "polish-prose: <slug> (generation note)" if it changed. Return HEAD and the leftover list.`,
  { label: 'record', phase: 'Record', schema: RECORD, effort: 'low' })

return {
  status: stable ? 'stable' : 'round-cap',
  article: ART,
  venue: VENUE || null,
  pangram: PANGRAM ? 'opted in' : 'off',
  roster: CRITICS,
  skipped,
  branch: pre.branch,
  baseline_sha: pre.baseline_sha,
  focus_file: pre.focus_file || null,
  humanize: hum,
  step6,
  rounds,
  final_read: finalRead ? { convergent: finalRead.convergent, focus_answers: finalRead.focus_answers, classes: finalRead.classes } : null,
  residue,
  rejected,
  closed_targets: closedTargets,
  record,
}
