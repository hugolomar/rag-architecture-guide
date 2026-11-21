---
description: Critical privacy rule prohibiting reading or indexing files inside docs/local/
trigger: always_on
---

# Privacy and Working Notes Boundary

The directory `docs/local/` is reserved strictly for personal and private developer working notes.

## Mandatory Invariant for AI Agents:
- Never read, grep, index, cite, or search files within `docs/local/`.
- Never base architectural decisions, feature implementations, or specifications on drafts in `docs/local/`.
- If a question arises regarding project scope, rely exclusively on official ADRs (`docs/adr/`), specifications (`specs/`), and the Constitution (`.specify/memory/constitution.md`).

