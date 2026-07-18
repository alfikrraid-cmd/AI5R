###############################################################################
# Engineering Practice
###############################################################################

ID            : EP-003
Title         : Branching Strategy
Status        : Approved
Version       : 1.0
Owner         : Engineering
Created       : 2026-07-18
Last Updated  : 2026-07-18

###############################################################################

# EP-003 Branching Strategy

**Status:** Approved Engineering Practice

**Date:** 2026-07-18

---

# Purpose

This Engineering Practice defines the Git branching strategy used by the AI5R
project.

The objective is to keep long-running development isolated while maintaining a
stable primary branch.

---

# Principles

- One branch = One major objective.
- One workspace = One major development stream.
- Never mix unrelated work in the same branch.
- Merge only after the branch reaches a stable state.

---

# Primary Branch

main

Purpose:

- Stable production-ready code
- Protected branch
- No direct experimentation

---

# Feature Branches

Naming convention:

feature/<topic>

Examples:

feature/repository-hygiene

feature/dashboard

feature/factory-packs

feature/n8n

feature/ui-theme

Feature branches contain active implementation work.

---

# Hotfix Branches

Naming convention:

hotfix/<topic>

Examples:

hotfix/login

hotfix/runtime-crash

Hotfix branches are reserved for urgent production fixes.

---

# Release Branches

Naming convention:

release/<version>

Examples:

release/v1.0

release/v2.0

Release branches are used for stabilization before merging into main.

---

# Branch Lifetime

A feature branch may exist for weeks or months.

Do not create new branches simply because a new MWO begins.

Multiple MWOs may be completed within the same feature branch when they belong
to the same development objective.

---

# Commit Policy

Commit frequently.

Each commit should represent one logical engineering change.

Avoid mixing unrelated modifications in a single commit.

---

# Merge Policy

Merge only when:

- implementation complete
- tests passing
- documentation updated
- code reviewed (when applicable)

---

# Workspace Mapping

Example:

~/AI5R

    feature/dashboard

~/AI5R-repo-hygiene

    feature/repository-hygiene

Each workspace should focus on a single long-running branch.

---

# Engineering Rules

Do not develop multiple unrelated objectives in the same branch.

Do not merge unstable branches into main.

Keep commit history clean and meaningful.

---

# Summary

Branching exists to isolate engineering work.

The branching strategy should maximize stability while allowing independent
development streams to progress safely.
