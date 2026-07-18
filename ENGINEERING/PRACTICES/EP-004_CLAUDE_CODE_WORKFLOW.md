###############################################################################
# Engineering Practice
###############################################################################

ID            : EP-004
Title         : Claude Code Workflow
Status        : Approved
Version       : 1.0
Owner         : Engineering
Created       : 2026-07-18
Last Updated  : 2026-07-18

###############################################################################

# Purpose

This Engineering Practice defines the official workflow for using Claude Code
on AI5R repositories.

The objective is to keep Claude Code sessions predictable, isolated, and safe,
and to prevent cross-repository or cross-objective contamination.

---

# Scope

This practice applies to every Claude Code session used for AI5R engineering
work, across all workspaces defined in EP-001 Development Workspaces.

---

# Principles

- One Claude session = One workspace.
- One Claude session = One engineering objective.
- Never edit multiple repositories from the same Claude session.
- CLAUDE.md is the primary entry point for project context.
- Engineering Practices are referenced, not duplicated, inside prompts.
- Prompts should stay minimal by relying on CLAUDE.md and the Engineering
  Practices it points to.
- Permanent decisions are recorded in Engineering Practice documents, not
  repeated in prompts.

---

# Workflow

## Starting a Session

1. Always start Claude Code from the repository root.
2. Verify the repository before starting any work:

       pwd
       git branch
       git status

3. Confirm the working directory, branch, and status match the intended
   engineering objective before giving Claude any instructions.

## During a Session

4. Work on exactly one engineering objective per session.
5. Do not switch to an unrelated objective inside the same session.
6. Do not open or edit a second repository from the same session. If work in
   another repository is required, start a new Claude Code session in that
   repository's own workspace, per EP-001.
7. Keep prompts minimal. Rely on CLAUDE.md and the Engineering Practices it
   references instead of restating workflow rules in the prompt.

## Ending a Session

8. Finish the current engineering objective before changing repositories.
9. Commit the work before ending the session.
10. Push the work before switching workspaces.

---

# Engineering Rules

1. One Claude session = One workspace. Never mix workspaces inside a single
   session.
2. Always start Claude Code from the repository root.
3. Always verify `pwd`, `git branch`, and `git status` before starting work.
4. One engineering objective per Claude session. Do not combine unrelated
   objectives.
5. Finish work before changing repositories.
6. Commit before ending a session.
7. Push before switching workspaces.
8. Never edit multiple repositories from one Claude session.
9. CLAUDE.md is the primary project entry point. Do not duplicate its content
   inside prompts.
10. Reference Engineering Practices instead of duplicating workflow rules in
    prompts or documents.
11. Keep prompts minimal by relying on CLAUDE.md and the Engineering
    Practices it references.
12. Preserve context by documenting permanent decisions in Engineering
    Practice documents instead of prompts.

---

# Summary

The Claude Code Workflow exists to keep each session focused, isolated, and
traceable to a single workspace and a single engineering objective. Starting
from a verified repository state, working on one objective at a time, and
closing each session with a commit and a push keeps AI5R's engineering
history clean and Claude Code's context reliable.
