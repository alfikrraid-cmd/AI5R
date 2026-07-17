# ADR-0001 — AI5R Lives in Repository, Not Chat

**Date:** 2026-06-28  
**Status:** ACCEPTED  
**Reviewer:** B (Founder)

---

## Context

AI5R was initially developed through long ChatGPT conversations. As the project grew, chat context became slow and inconsistent across sessions.

---

## Decision

AI5R's canonical memory and identity will live in the GitHub repository.

Chat is working memory only.

---

## Consequences

### Easier

- Start new chat without losing AI5R identity.
- Use multiple AI models with the same source of truth.
- Track decisions through Git history.

### Harder

- Requires repository discipline.
- Requires keeping Bootstrap and Current State updated.
