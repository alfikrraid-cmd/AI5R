# 07 — DEVELOPMENT RULES
**Document ID:** AI5R-CONST-007  
**Version:** 1.0.0  
**Owner:** B (Founder)  
**Status:** CANONICAL

---

## Purpose

These rules govern every line of code, every workflow node, every prompt, and every configuration file produced by AI5R. They are not suggestions. Deviation requires explicit documented justification.

---

## Rule Set 1 — Universal Rules (All Output Types)

### R1.1 — Every artifact must have an identity
```
Name     : Human-readable
ID       : Machine-readable, unique, uppercase
Version  : Semantic (MAJOR.MINOR.PATCH)
Owner    : AI5R or specific sub-system
Status   : DRAFT | ACTIVE | DEPRECATED | ARCHIVED
```

### R1.2 — Every artifact must have a contract
Define before building:
- **Input:** What does it accept? (type, format, required/optional)
- **Output:** What does it produce? (type, format, guaranteed fields)
- **Side Effects:** What does it modify externally? (must be explicit)

### R1.3 — Every artifact must have tests
Minimum test coverage:
- Happy path (valid input → expected output)
- Edge case (boundary values, empty input, max input)
- Failure case (invalid input → expected error, not crash)

### R1.4 — Every artifact must have documentation
Minimum documentation:
- Purpose (one sentence)
- Input/Output (with examples)
- How to run / trigger
- How to roll back

### R1.5 — Every artifact must have a rollback path
Before deployment: snapshot created.  
Rollback must be tested, not assumed.

---

## Rule Set 2 — Code Rules

### R2.1 — Code must compile on first attempt
AI5R does not ship code that has not been tested to run. If testing is not possible, this must be explicitly flagged and a test plan provided.

### R2.2 — Code must be modular
- Maximum function length: 50 lines (extract if longer)
- Maximum file length: 300 lines (split if longer)
- One responsibility per function
- One responsibility per file

### R2.3 — No magic numbers or strings
```python
# BAD
if status == 3:
    ...

# GOOD
STATUS_COMPLETE = 3
if status == STATUS_COMPLETE:
    ...
```

### R2.4 — No duplicated logic
If the same logic appears in two places, it must be extracted to a shared module. The third occurrence is a violation.

### R2.5 — Error handling is mandatory
Every function that can fail must handle failure explicitly:
- Define what "failure" means for this function
- Return structured errors (not raw exceptions to the caller)
- Log errors with context (what was being attempted, what failed)

### R2.6 — Dependencies must be pinned
No `"latest"` in package files. No unversioned imports. Every dependency is pinned to a specific version in production.

---

## Rule Set 3 — Workflow (n8n) Rules

### R3.1 — Maximum 15 nodes per canvas
Larger workflows use sub-workflows called via Execute Workflow node.

### R3.2 — Every node must be labeled
No unnamed nodes. Label format: `[NN] Action Name`  
Example: `[01] Parse Requirements`, `[05] QA Gate`

### R3.3 — Error paths must be explicit
Every node that can fail must have a connected error handler. Silent failures are violations.

### R3.4 — No hardcoded credentials
All credentials reference n8n Credential store. No API keys in node parameters.

### R3.5 — AI nodes must have temperature set explicitly
Default temperature is not acceptable. Set temperature based on task type:
- Deterministic tasks (classification, extraction): 0.0–0.2
- Structured generation (specs, contracts): 0.2–0.5
- Creative generation (content, prompts): 0.5–0.8

### R3.6 — Every workflow has a test fixture
A static input file that exercises the complete happy path, minimum one edge case.

---

## Rule Set 4 — Prompt Rules

### R4.1 — Every prompt has a role declaration
System prompt must declare the AI's role before task instructions.

### R4.2 — Every prompt has explicit output format
Tell the model exactly what format to return. Never leave format ambiguous.

### R4.3 — Prompts are versioned
Prompt ID format: `PROMPT-{ENGINE}-{NNN}-v{VERSION}`  
Example: `PROMPT-REQ-001-v1.2`

### R4.4 — Prompts have test cases
Minimum three test inputs with expected outputs per prompt.

### R4.5 — Token budget is managed
Every AI node must have an estimated token count. High-token prompts require explicit approval.

---

## Rule Set 5 — Output Quality Rules

### R5.1 — No ugly output
AI5R produces premium-quality output at all times. This applies to:
- HTML → valid, styled, responsive
- PDF → professional layout, correct fonts
- SVG → clean paths, correct viewBox
- JSON → properly formatted, no trailing commas
- Markdown → consistent headings, no broken links

### R5.2 — Output must be immediately usable
No output requires manual cleanup before it can be used. If cleanup is needed, the engine has failed.

### R5.3 — Every output is sellable
Ask before shipping: "Would a paying customer accept this?" If no, do not ship.

---

## Development Checklist (Per Artifact)

Before marking any artifact as COMPLETE:

- [ ] Identity fields filled (Name, ID, Version, Owner, Status)
- [ ] Input/Output contract defined and documented
- [ ] Happy path test passes
- [ ] Edge case tests defined
- [ ] Failure case handled with structured error
- [ ] Documentation written
- [ ] Rollback path confirmed
- [ ] Version tagged
- [ ] Changelog entry added
- [ ] Founder notified if Tier 2+ decision was made
