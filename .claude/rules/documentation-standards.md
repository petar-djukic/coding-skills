<!-- Copyright (c) 2026 Petar Djukic. All rights reserved. SPDX-License-Identifier: MIT -->

# Documentation Standards

Distilled from `docs/constitutions/design.yaml`. Read the full constitution for document type schemas, completeness checklists, and naming conventions.

## Specification-Driven Development

Specifications are the source of truth. Code serves specifications, not the other way around. No implementation code before the PRD and use case exist. No implementation issue before a test suite exists for its use case.

## YAML-First

Use YAML for structured documents (VISION, ARCHITECTURE, PRDs, use cases, test suites). Use markdown for prose-heavy guidelines and specification summaries. YAML is machine-readable by design.

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

All diagrams in Mermaid, defined inline in markdown fenced code blocks. Do not create separate image files.

## Document Types and Locations

| Type | Location | Format |
|------|----------|--------|
| Vision | `docs/VISION.yaml` | vision-format |
| Architecture | `docs/ARCHITECTURE.yaml` | architecture-format |
| PRD | `docs/specs/product-requirements/prd[NNN]-[feature-name].yaml` | prd-format |
| Use case | `docs/specs/use-cases/rel[NN].[N]-uc[NNN]-[short-name].yaml` | use-case-format |
| Test suite | `docs/specs/test-suites/test-rel-[release-id].yaml` | test-case-format |
| Engineering guideline | `docs/engineering/eng[NN]-[short-name].yaml` | engineering-guideline-format |
| Specification | `docs/SPECIFICATIONS.yaml` | specification-format |
| Roadmap | `docs/road-map.yaml` | — |

## Traceability Chain

Vision (goals) -> Architecture (components) -> PRDs (numbered requirements) -> Use cases (tracer bullets) -> Test suites (validation) -> Code (implementation, traces to PRDs via commits).

Every PRD traces to VISION and ARCHITECTURE. Every use case traces to PRDs via touchpoints. Every test suite traces to use cases via the traces field.

## Test Suite Linkage

Every use case must have a corresponding test suite. The test suite validates the use case's success criteria with explicit inputs and expected outputs.

## Roadmap-Driven Releases

Use cases are assigned to releases in `road-map.yaml`. Releases are numbered `rel[NN].[N]`. Minor releases validate completed major releases without renumbering existing use cases.
