# AI5R IT Agent Foundation

An IT engineering layer for AI5R, added by MWO-IT-001. Scope: helps
diagnose and fix engineering issues ("IT: <problem>" tasks) across ALL
AI5R modules — not just LTSA. Entry point: `.claude/skills/ai5r-it-orchestrator/SKILL.md`.

## Core decision

**AI5R owns orchestration.** The vendored ECC (github.com/affaan-m/ECC)
agents/skills under `.claude/agents/` and `.claude/skills/` are a
specialist reference LIBRARY only. No ECC agent is authoritative over
AI5R workflow, and no ECC orchestration behavior (its own chief-of-staff,
plan-orchestrate, team-agent-orchestration patterns) is used — those were
evaluated and rejected specifically because AI5R already has its own
orchestration (this layer) and its own change-management convention (MWO).

**Never run `/plugin install ecc@ecc` or `/plugin marketplace add
https://github.com/affaan-m/ECC` in this repo.** That installs all 68
agents, 286 skills, 94 command shims, hooks, and MCP configs — everything
this foundation deliberately did not vendor. If a future task needs a
specialist not in the current vendored set, vendor that ONE file at a
reviewed, pinned commit (see `ECC-ATTRIBUTION.md` for the process), the
same way this set was built. Do not bulk-install.

## What was vendored, and why only this much

13 agents + 13 skills (26 total), pinned to ECC commit
`656d4b5746413e4e78f9c62cb34d686515931f4f`. Full list, per-file rationale,
and the rejected candidates (with the specific content that got them
rejected) are in `ECC-ATTRIBUTION.md`. Short version: AI5R's real running
stack today is Python/FastAPI + React + PostgreSQL + Docker Compose + n8n
(webhooks-as-gateways). Everything vendored maps to that stack or to a
role in the 12-role list below; nothing for languages/frameworks/domains
AI5R doesn't use.

## The 12 roles

Orchestrator, Architecture, Backend/FastAPI, Frontend, PostgreSQL/Data,
DevOps/Docker, TDD/Test, Code Review, Security, Incident/Debug,
Observability, Docs/Memory. Role -> specialist mapping lives in
`ai5r-it-orchestrator/SKILL.md`, not duplicated here (single source of
truth — update the skill file, not this README, when the mapping
changes).

## MWO discipline is unchanged

This layer does not invent a parallel ticket/change-management system.
Real product changes made through this layer still get an MWO number and
a report under `ENGINEERING/MWO/`, following the existing naming
convention, exactly like every other change in this repository. A
read-only investigation with no code change is recorded in
`ENGINEERING/IT-AGENT/MEMORY/` instead — it doesn't need an MWO.

## Evidence hierarchy

CODE/RUNTIME/DB/WIRING evidence > documentation (MWO reports, ADRs, code
comments) > IT memory. This repo's own comments are unusually elaborate
and have been observed to describe something that was later orphaned or
never actually wired up — always re-verify current state before acting,
regardless of how confident the documentation sounds.

## Hard safety (unconditional)

No production DB writes. No schema migration. No destructive command. No
secret/credential changes. No production deploy/restart/recreate. No n8n
workflow mutation. No unrelated refactor. No direct edits to the
production checkout — all implementation work happens in a dev clone on a
feature branch, reviewed and merged through the normal process before any
deploy.

## Token/context discipline

Only vendored-file names + one-line descriptions are ever resident in
context by default. Full agent/skill bodies load only when the
orchestrator explicitly dispatches them for a classified task (default 1,
max 2 specialists). No hooks, no MCP servers — zero added cost on
conversation that isn't an explicit "IT:" task. IT memory is read
selectively (grep the relevant file/entry), never loaded wholesale.
