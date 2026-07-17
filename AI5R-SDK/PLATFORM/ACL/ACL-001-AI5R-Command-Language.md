# ACL-001 — AI5R Command Language

```
Status: FROZEN — canonical
Artifact ID: ACL-001
Artifact Name: AI5R Command Language
Artifact Type: Canonical Operating Language
Owner: AI5R Platform
Consumers: Humans; AI Workers; AI5R Runtime
Established by: MWO-PLATFORM-001 (ENGINEERING/MWO/MWO-PLATFORM-001-AI5R-Command-Language.md)
Related: AI5R-SDK/PLATFORM/MANUFACTURING/UMR-001-Universal-Manufacturing-Runtime-Specification.md
         (execution and Target-resolution authority); CONSTITUTION/13_ENGINEERING_EXECUTION_PROTOCOL.md
         (the Default Execution Model every ACL command maps to)
```

Engineering stores work. Platform stores artifacts. This document lives under `AI5R-SDK/PLATFORM/` because it is a Canonical Platform Artifact, not engineering work-in-progress — the MWO that produced it remains under `ENGINEERING/MWO/`.

---

## 1. What ACL Is

The AI5R Command Language is an **Operating Language** — not a scripting language, not a programming language. It has no interpreter, no syntax tree, no runtime of its own. An ACL command is a directive of intent, issued in natural language.

## 2. ACL Principles

- **Intent over implementation.** A command states what is meant, never how it happens.
- **Execution belongs to UMR.** ACL never performs, simulates, or re-implements execution.
- **One command, one intent.** Each command names exactly one thing.
- **No runtime logic.** ACL-001 contains no lifecycle, no state machine, no pipeline of its own.
- **No implementation logic.** ACL-001 contains no code, and authorizes none by itself.
- **Human-first, machine-readable second.** A command must read as a natural instruction to a person before it is ever parsed by a machine.
- **Never exposes implementation details.** A command names intent and target; it never references file paths, class names, function signatures, or internal mechanics.
- **ACL is stable. Runtime evolves.** The grammar and vocabulary here do not change when an executing runtime (e.g. UMR-001) changes underneath it.

## 3. ACL Grammar

**Sentence = Verb + Target + Optional Context.**

- **Verb** — one of the seven commands (§4).
- **Target** — the thing the command applies to, named in plain language.
- **Optional Context** — a natural-language qualifier narrowing scope, product, or focus. Never a parameter list, never a flag, never a key-value pair.

Commands are expressed as intent, not as API operations.

**Examples:**
```
Chief.
Manufacture Pump.

Chief.
Research Knowledge Graph.

Chief.
Review MWO-050.

Chief.
Status LTSA.
```
"Chief." is speaker attribution — who is issuing the command — not part of the Grammar itself.

### 3.1 Canonical Target Space

| Target Kind | Grounded In |
|---|---|
| **Artifact** | A produced output — e.g. a Company/Department Artifact, or a Platform Artifact such as ACL-001 or UMR-001. |
| **Factory Pack** | `AI5R-SDK/FACTORY/PACKS.FactoryPack` — per UMR-001 §1/§11. |
| **Platform** | An AI5R Platform-level peer asset — Knowledge, Capability, BRAIN, Factory, Runtime, Foundation — per ADR-003. |
| **Product** | A named, versioned Enterprise Object registered under `PRODUCTS/`, per ADR-001. |
| **Capability** | A named execution capability, per ADR-003's universal execution layer. |
| **Worker** | A Human or AI Worker occupying a Role, per the Role Manufacturing Recipe. |
| **Knowledge** | A Knowledge Foundation / Knowledge Warehouse asset, per `AI5R-ARCHITECTURE-SPEC-v2.0.md`. |
| **MWO** | A Manufacturing Work Order, referenced by ID. |

Canonical Target Space is an **address vocabulary** — it names the space a Target is drawn from so it can be resolved (§3.2). It is not a runtime type system: ACL performs no type-checking, no validation, no enforcement against it.

### 3.2 Target Resolution

ACL names Target. UMR resolves Target.

Naming a Target is an act of intent, complete on its own within ACL. Turning that name into a concrete, addressable thing belongs to UMR, not to ACL — mirroring, at the Target level, the same division §7 establishes at the command level.

## 4. Commands

**Research** — investigation only. Maps to Read → Understand → Verify.

**Resume** — restores general project context from what's already persisted. Maps to Read → Understand → Verify, scoped to context recovery.

**Load** — brings one specific, named artifact into working context by reference. Narrower than Resume. Maps to Read → Understand → Verify, scoped to a single artifact.

**Manufacture** *(canonical)* — produces real, tested, working output against approved scope. Maps to Implement → Validate. Where the work is Factory-Pack/UMC-001 object manufacturing, UMR-001 is the execution authority. Otherwise, maps directly to the existing Implement → Validate phase. **Implement is a legacy alias for Manufacture** — identical meaning, no independent behavior.

**Review** — presents findings or completed work for Chief Architect judgment. Maps to Report → STOP → Wait for Chief Architect approval.

**Status** — reports current known state, read-only, no approval sought. Maps to Report, without the STOP-for-approval step.

**Commit** — persists approved work to git history. Maps to the Git Policy: one MWO, one commit, separate explicit approval.

## 5. Operating Modes

Research, Manufacture, Review, and Commit are Operating Modes — sustained phases of work. Resume, Load, and Status are first-class commands, not Operating Modes — each completes in a single action.

## 6. Workflow Mapping (no second workflow introduced)

| Command | Existing Workflow Phase | Source |
|---|---|---|
| Research | Read → Understand → Verify | Constitution §13 |
| Resume | Read → Understand → Verify (general recovery) | Constitution §13 |
| Load | Read → Understand → Verify (single artifact) | Constitution §13 |
| Manufacture / Implement (legacy) | Implement → Validate | Constitution §13; **UMR-001** where Factory-Pack/UMC-001 scope applies |
| Review | Report → STOP → Wait for Chief Architect approval | Constitution §13 |
| Status | Report (informational only) | Constitution §13 |
| Commit | Git Policy — one MWO, one commit | Constitution §13 |

## 7. Independence from UMR

ACL-001 describes the language. UMR-001 executes it, and resolves its Targets, where execution applies. This document does not restate UMR-001's internals — see `AI5R-SDK/PLATFORM/MANUFACTURING/UMR-001-Universal-Manufacturing-Runtime-Specification.md` directly.

## 8. What ACL Does Not Do

- Does not grant authority beyond the existing Chain of Command.
- Does not create a second approval mechanism, execution model, Git policy, or manufacturing runtime.
- Does not become executable tooling by virtue of this specification.

## 9. ACL Evolution Policy

Any future command must conform to the canonical grammar (§3). Backward compatibility is mandatory: an existing command's meaning and workflow mapping may be extended but never silently changed or removed. A legacy alias, once established, remains valid indefinitely without a separate, explicit Chief Architect decision to retire it.
