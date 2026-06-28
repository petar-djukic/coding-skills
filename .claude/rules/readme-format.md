<!-- Copyright (c) 2026 Petar Djukic. All rights reserved. SPDX-License-Identifier: MIT -->

# README Format

README files are the public interface of a repository. They are read by engineers, hiring managers, and automated profile-correlation platforms. A README should read like a technical brief written by someone who builds production systems.

## Author Context

The repository owner is a Principal Architect with over 20 years of production systems experience, a PhD in Computer Engineering, and 64 US patents. READMEs must reflect this level of experience: confident, precise, and substantive. Never write anything that reads like a tutorial, a sales pitch, or a job application.

## Structure

Order matters. A reader who scans only the first three sections should understand what the project is, why it exists, and how it works at an architectural level.

1. **Title and one-line description** -- What the system does, in domain terms. No adjectives, no taglines. The title is the repository name; the description is a single sentence.

2. **Architectural thesis** -- The "why" in 2-4 sentences. What engineering problem does the approach solve? Methodology (e.g., spec-driven development, differential testing) is introduced here as the solution to a stated problem, not as a label.

3. **System diagram** -- Mermaid showing component relationships, the development pipeline, or the data flow. Architecture diagrams signal systems thinking more effectively than any paragraph. Use fenced code blocks with `mermaid` language tag. Do not use PlantUML (GitHub does not render it).

4. **Project scope and status** -- What is the target, what is built, what is planned. Use concrete numbers (e.g., "12 of 123 utilities specified"). Scope demonstrates ambition; status demonstrates execution.

5. **Methodology or approach** -- How the system is built, not how to use it. Describe the engineering pipeline or workflow. This section lets the approach speak for itself. Keep it factual.

6. **Repository structure** -- A brief tree showing the top-level layout. Annotate each entry with its role (one phrase, not a sentence).

7. **Technology choices** -- Brief, with rationale. "Go because X" is more informative than "Built with Go." Only include choices that are non-obvious or have an interesting reason behind them.

8. **Build and test instructions** -- The conventional README content. Last, not first. Engineers who need this will scroll; engineers who are evaluating the project need the sections above.

## Principles

- **No buzzwords.** If a term would not survive a technical design review, do not use it. "Agentic orchestration" is acceptable if the system actually orchestrates agents. "Self-healing MLOps" is not acceptable unless the system literally does that.
- **No emoji in headers or body text.** This is an engineering artifact.
- **No keyword stuffing.** Do not add terms for discoverability. Let the description of the work contain the relevant terms naturally.
- **Let the work demonstrate competence.** A README that explains a sophisticated approach clearly is more impressive than one that tells you it is impressive.
- **Write for a 30-second scan.** The title, thesis, and diagram must stand alone for readers who go no further.
- **Link to deeper documentation.** If the repository has architecture docs, specs, or design documents, link to them from the relevant sections. Do not reproduce their content in the README.
- **Active voice, present tense.** "The harness compares outputs" not "Outputs are compared by the harness."
- **Concrete over abstract.** Prefer "123 Unix utilities" over "a large number of tools." Prefer "runs both binaries with identical inputs and compares stdout byte-for-byte" over "performs comprehensive testing."
