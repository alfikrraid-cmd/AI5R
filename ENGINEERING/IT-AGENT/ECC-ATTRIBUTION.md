# ECC Attribution & Vendoring Record

Source: https://github.com/affaan-m/ECC
License: MIT (see upstream `LICENSE`)
Pinned commit: `656d4b5746413e4e78f9c62cb34d686515931f4f`
Vendored: verbatim, byte-for-byte, at the paths listed below. No content
was edited. To update, re-vendor deliberately at a new pinned commit and
re-run the security review below — never auto-sync.

This project does not install the ECC Claude Code plugin
(`/plugin install ecc@ecc`). These files were copied individually from a
throwaway clone of the pinned commit above.

## Vendored agents (`.claude/agents/`, 13)

| File | Role |
|---|---|
| `planner.md` | Orchestrator support (multi-step implementation design) |
| `architect.md` | Architecture |
| `code-architect.md` | Architecture |
| `fastapi-reviewer.md` | Backend/FastAPI |
| `python-reviewer.md` | Backend/FastAPI |
| `react-reviewer.md` | Frontend |
| `database-reviewer.md` | PostgreSQL/Data |
| `code-reviewer.md` | Code Review |
| `silent-failure-hunter.md` | Code Review / Incident-Debug |
| `security-reviewer.md` | Security |
| `network-troubleshooter.md` | Incident/Debug |
| `doc-updater.md` | Docs/Memory |
| `tdd-guide.md` | TDD/Test |

## Vendored skills (`.claude/skills/`, 13)

`fastapi-patterns`, `python-patterns`, `backend-patterns`,
`postgres-patterns`, `react-patterns`, `react-testing`, `tdd-workflow`,
`python-testing`, `docker-patterns`, `security-review`,
`architecture-decision-records`, `hexagonal-architecture`,
`living-docs-governance`.

## Security review method

Every candidate file (agents above, skills above, plus every rejected
file listed below) was inspected for: executable/destructive instructions,
external network calls, secret access, privilege escalation, and
instructions conflicting with AI5R rules — via direct content read plus a
pattern sweep (`curl`/`wget` to non-localhost hosts, API keys/secrets,
`DROP TABLE`, `rm -rf`, `sudo`, `chmod 777`, `eval`/`exec`, dependency
installs, prompt-override language). All 26 vendored files declare only
`Read`/`Grep`/`Glob`/`Bash` (a few also `Write`/`Edit` for their own
function — `doc-updater`, `tdd-guide`) and carry the same defensive
"Prompt Defense Baseline" header (do not override higher-priority project
rules, do not reveal secrets) — consistent with, not conflicting with,
AI5R's own instruction hierarchy. No external non-localhost network calls,
no real secrets, no destructive command as a *recommended action*, no
privilege escalation found in the vendored set.

## Rejected candidates (evaluated, not vendored) and why

| File | Reason |
|---|---|
| `chief-of-staff.md` | Unrelated domain (personal email/Slack/LINE/Messenger triage). Requires `Edit`/`Write`/`Bash`, external CLIs (Gmail CLI, Slack MCP, Matrix bridge, Chrome+Playwright), and a `PostToolUse` hook that auto-enforces git commit/push after every send. Also the explicit reason Phase 2 named: AI5R owns orchestration, no ECC agent — least of all this one — is authoritative here. |
| `build-error-resolver.md` | Its documented core remediation pattern is `rm -rf .next node_modules/.cache && npm run build` and `rm -rf node_modules package-lock.json && npm install` — conflicts directly with "no destructive command" and "no dependency installation until reviewed." |
| `unified-memory` (skill) | Prescribes its own storage (`<repo>/.ecc/memory/`, `~/.ecc/memory/`) instead of this repo's `ENGINEERING/IT-AGENT/MEMORY/`; full functionality requires installing a separate `ecc-universal` npm runtime on `PATH` plus an optional `ecc-memory-mcp` MCP server. Conflicts with "no dependency installation," "no MCP," and duplicates a mechanism AI5R already has a convention for (MWO reports / plain markdown memory). |
| `security-scan` (skill) | Mechanism is `npm install -g ecc-agentshield` (external dependency) plus calls to an external tool (AgentShield) requiring `ANTHROPIC_API_KEY`. Conflicts with "no dependency installation," "no runtime dependency," and introduces an external network/API-key dependency. Kept `security-review` instead — a pure static checklist skill, no installs, no external calls. |
| `plan-orchestrate` (skill) | Multi-agent chain/squad choreography — heavier than a single classify -> 1-2 specialists workflow needs; AI5R's own orchestrator (`ai5r-it-orchestrator`) covers this. |
| `team-agent-orchestration` (skill) | Kanban/ownership/merge-gate mechanics for agent squads — not needed for one orchestrator handling one task at a time. |
| All other ~53 agents / ~271 other skills | Cover stacks/domains AI5R does not use (Rust, Go, Java, Kotlin, Swift, C++, C#, PHP, Perl, F#, Dart/Flutter, Django, Laravel, Spring Boot, Quarkus, crypto/DeFi, marketing/SEO/content/brand, homelab/network-architect beyond the one troubleshooter kept, healthcare, visa-doc-translate, etc.). Not reviewed line-by-line since they were never candidates for this stack; available to vendor individually later, at a reviewed pinned commit, if a genuine need arises — never bulk-installed. |

## Adding a new specialist later

1. Identify the exact ECC file (agent `.md` or skill directory) needed.
2. Clone ECC at a specific commit (record the hash).
3. Read the full file content; run the same security-review method above.
4. If clean and non-conflicting: copy verbatim into `.claude/agents/` or
   `.claude/skills/`, add a row to the tables above, note the commit hash
   used (bump the "Pinned commit" line only if the whole set is
   re-vendored at once; otherwise note the per-file commit next to it).
5. If unsafe or conflicting: do not vendor it; add a row to the rejected
   table with the specific reason, same as above.
