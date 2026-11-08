<!-- Copyright (c) 2026 Petar Djukic. All rights reserved. SPDX-License-Identifier: MIT -->

# Documentation Standards

Distilled from `docs/constitutions/design.yaml`. The constitution ships with each target repository, not with this skills repository; read it there for document type schemas, completeness checklists, and naming conventions.

## Specification-Driven Development

Specifications are the source of truth. Code serves specifications, not the other way around. No implementation code before the SRD and use case exist. No implementation issue before a test suite exists for its use case.

## Choosing a Document Type

For documents aimed outside the repository (papers, whitepapers, RFCs,
specifications, invention disclosures), pick the form from
[technical-document-types.md](https://github.com/petar-djukic/writing-skills/blob/main/.claude/rules/technical-document-types.md)
(now in writing-skills). The YAML
types below govern documents inside the repository.

## YAML-First

Use YAML for structured documents (VISION, ARCHITECTURE, SRDs, use cases, test suites). Use markdown for prose-heavy guidelines and specification summaries. YAML is machine-readable by design.

## Writing Style

- Concise, active voice, specific and concrete language, no unnecessary words (Elements of Style).
- Use the royal "we" in active voice. GOOD: "We implement the feature..." BAD: "This document describes..."
- Paragraph form unless not possible. Vary sentence length. Short paragraphs only to emphasize.
- Tables instead of lists for short entries. Name all tables.
- Explain abbreviations at least once per document section.
- Do not use bold text or horizontal rules in prose.

## Forbidden Terms

Do not use: critical, critically, key, deliberate, strategic, precisely, absolutely, fundamental, breakthrough, principled, honest, at the heart of, grounded, standards-aligned.

## Diagrams

Mermaid is the default. The form follows where the figure is read and which notation it needs.

Table: Diagram form by use

| Use | Form | Why |
|------|------|-----|
| Specifications, READMEs, simple flow and component diagrams | Mermaid, inline in a fenced `mermaid` block | GitHub renders it in place, with no committed image and no build step |
| UML notation (deployment, component, class, state, activity, use case) and paper figures | d2 source committed beside its rendered PNG, embedded as a markdown image | Mermaid has no UML deployment diagram; one d2 source compiles to the paper's PDF and the wiki's PNG; a PNG renders in every viewer, including ones that show Mermaid fences as raw code |
| Wiki figures | SVG files under `figures/` beside the wiki, embedded as markdown images | renders in any markdown viewer (Obsidian, a plain preview), and `mage wiki` inlines it theme-aware |

Commit the d2 source with its PNG, and regenerate the PNG in the same commit as any change to the source; an image whose source is missing or out of date cannot be maintained. Draw wiki SVGs in the Loom palette (ink `#20262c`, ground `#f6f7f5`, accent `#c0612b`) with a full-size ground rectangle, which is what lets `mage wiki` swap the theme. The Loom wiki (`petar-djukic/autogenic-systems`, `agent-dsl/wiki.md`) is the reference. Do not use PlantUML: GitHub does not render it. A repository may still narrow this further in its own rules, as autogenic-systems does by drawing every diagram in d2.

## Document Types and Locations

| Type | Location | Format |
|------|----------|--------|
| Vision | `docs/VISION.yaml` | vision-format |
| Architecture | `docs/ARCHITECTURE.yaml` | architecture-format |
| SRD | `docs/specs/software-requirements/srd[NNN]-[feature-name].yaml` | srd-format |
| Use case | `docs/specs/use-cases/rel[NN].[N]-uc[NNN]-[short-name].yaml` | use-case-format |
| Test suite | `docs/specs/test-suites/test-rel-[release-id].yaml` | test-case-format |
| Engineering guideline | `docs/engineering/eng[NN]-[short-name].yaml` | engineering-guideline-format |
| Specification | `docs/SPECIFICATIONS.yaml` | specification-format |
| Roadmap | `docs/road-map.yaml` | — |

## Traceability Chain

Vision (goals) -> Architecture (components) -> SRDs (numbered requirements R1..., acceptance criteria AC1...) -> Use cases (tracer bullets) -> Test suites (validation) -> Code (implementation, traces to SRDs via commits).

Every SRD traces to VISION and ARCHITECTURE. Every use case traces to SRDs via touchpoints naming SRD requirement IDs. Every test suite traces to use cases and SRD acceptance criteria via the traces field.

## Test Suite Linkage

Every use case must have a corresponding test suite. The test suite validates the use case's success criteria with explicit inputs and expected outputs.

## Roadmap-Driven Releases

Use cases are assigned to releases in `road-map.yaml`. Releases are numbered `rel[NN].[N]`. Minor releases validate completed major releases without renumbering existing use cases.
