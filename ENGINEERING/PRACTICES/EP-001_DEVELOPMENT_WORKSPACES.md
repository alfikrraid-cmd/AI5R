# Development Workspaces

**Status:** Approved Engineering Practice
**Date:** 2026-07-18

---

# Purpose

AI5R uses one Git working directory per major development stream.

This prevents:

- branch conflicts
- unnecessary stash/reset
- accidental overwrites
- mixed implementations
- unrelated Claude Code context

---

# Principle

One workspace = One major development stream

Do not reuse the same Git working directory for unrelated long-running work.

---

# Workspace Examples

~/AI5R
    Active UI / Dashboard development

~/AI5R-repo-hygiene
    Repository Hygiene
    N8N Foundation

Future examples:

~/AI5R-factorypacks
    Factory Packs

~/AI5R-release
    Release Stabilization

---

# Remote Development

When working outside the office:

Laptop
    ↓
MobaXterm (SSH)
    ↓
VPS
    ↓
Claude Code
    ↓
Git

The laptop acts only as a terminal.

All development is executed on the VPS.

---

# Benefits

- isolated repositories
- safer branch management
- cleaner Git history
- easier recovery
- better Claude Code context
- avoids checkout conflicts

---

# Engineering Rule

Before starting a new major development stream:

1. Create a dedicated repository clone.
2. Checkout the required branch.
3. Keep unrelated work in separate workspaces.
4. Avoid switching unrelated long-lived branches inside the same working directory.

---

# Example

UI Development

    cd ~/AI5R
    claude

Repository Hygiene

    cd ~/AI5R-repo-hygiene
    claude

---

This document records the engineering practice adopted after introducing
parallel development workspaces for AI5R.
