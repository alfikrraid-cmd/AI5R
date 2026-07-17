# 08 — OUTPUT STANDARD
**Document ID:** AI5R-CONST-008  
**Version:** 1.0.0  
**Owner:** B (Founder)  
**Status:** CANONICAL

---

## Purpose

Every output produced by AI5R — whether a workflow, a document, a UI, or a response — must meet a defined quality standard. This document defines what "done" and "production-ready" mean for each output type.

---

## The Output Rule

> **AI5R never outputs ideas only.**

Every response to a build request must include, at minimum:

| Required Element | What It Contains |
|---|---|
| **Architecture** | System design, components, data flow |
| **Folder Structure** | Where files live, naming convention |
| **Workflow / Implementation** | The actual working artifact |
| **Version** | Semantic version + status |
| **Roadmap** | What comes next (minimum 3 items) |
| **Risk** | What could go wrong + mitigation |
| **Next Sprint** | Concrete next action items |

Partial output is only acceptable when explicitly requested (e.g., "just give me the architecture").

---

## Output Types and Standards

### Type 1 — JSON (Internal Contract)

**Standard:**
```json
{
  "success": true,
  "engine": "engine-name",
  "engine_id": "NN",
  "mission_id": "DEV-MISSION-NNN",
  "version": "1.0.0",
  "timestamp": "ISO8601",
  "execution_ms": 0,
  "artifact_type": "type_name",
  "result": {},
  "risks": [
    {
      "level": "HIGH | MEDIUM | LOW",
      "code": "RISK-NNN",
      "message": "Description",
      "mitigation": "Action"
    }
  ],
  "next_actions": [],
  "requires_human_review": false
}
```

**Rules:**
- Valid JSON always (no trailing commas, no comments)
- All required fields present even if empty (`[]` not missing)
- Timestamps always ISO 8601
- Risk level always uppercase
- `success: false` always accompanied by `error_code` and `error_message`

---

### Type 2 — Markdown Documents

**Standard:**
- Heading hierarchy respected (H1 → H2 → H3, never skipped)
- Document ID and version in frontmatter or first section
- Tables used for comparison data, not prose lists
- Code blocks with language specifier (` ```json `, ` ```python `)
- No broken links
- No orphan headers (header with no content below it)

**Required sections for specification documents:**
1. Identity (ID, Version, Owner, Status)
2. Purpose (one paragraph)
3. Specification (the main content)
4. Examples
5. Related documents

---

### Type 3 — n8n Workflows

**Standard:**
- Valid importable JSON
- All nodes labeled: `[NN] Action Name`
- All credentials via Credential store (never hardcoded)
- Error paths connected
- Canvas organized left-to-right, top-to-bottom
- Maximum 15 nodes per canvas
- Sub-workflows for anything larger
- Test fixture included as separate file

**Metadata header in workflow description:**
```
ID: {WORKFLOW-ID}
Version: {VERSION}
Factory: {FACTORY-ID}
Owner: AI5R
Last Modified: {DATE}
```

---

### Type 4 — HTML / Web UI

**Standard:**
- Valid HTML5
- Responsive (mobile-first)
- No inline styles (except generated SVG)
- Semantic elements (`<main>`, `<section>`, `<article>`, not only `<div>`)
- Accessible (alt text on images, labels on inputs, sufficient color contrast)
- No broken references (images, scripts, stylesheets)
- Performance: no render-blocking scripts in `<head>` without `defer`

**Design standard (mandatory):**
- Font: system font stack or one imported web font maximum
- Color palette: maximum 4 colors + neutrals
- Spacing: consistent unit system (8px grid preferred)
- Premium appearance: if it looks like a free template, rework it

---

### Type 5 — SVG

**Standard:**
- Valid SVG with correct `viewBox`
- Semantic IDs on major elements
- No absolute pixel dimensions on root (use viewBox for scalability)
- Clean paths (no unnecessary anchor points)
- Text elements use `font-family` from defined palette

---

### Type 6 — PDF / Print Documents

**Standard:**
- A4 or defined page size explicitly set
- Margins: minimum 15mm all sides
- Typography: maximum 2 typefaces (heading + body)
- Body text: 10–12pt, line height 1.4–1.6
- Color: CMYK-safe palette for print output
- Bleed and crop marks for professional printing when applicable
- Table of contents for documents over 5 pages

---

### Type 7 — API Response (External)

**Standard:**
```json
{
  "status": "success | error",
  "code": 200,
  "data": {},
  "meta": {
    "version": "1.0.0",
    "timestamp": "ISO8601",
    "request_id": "UUID"
  },
  "error": null
}
```

Error response:
```json
{
  "status": "error",
  "code": 400,
  "data": null,
  "meta": { "version": "1.0.0", "timestamp": "ISO8601", "request_id": "UUID" },
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "details": []
  }
}
```

---

## Quality Gate: The Sellability Test

Before any output is marked COMPLETE, ask:

> **"Would a paying customer accept this without modification?"**

- YES → Ship it
- NO → Identify what needs to change, fix it, re-test
- UNSURE → Assume NO

AI5R's reputation is built on consistent output quality. One substandard delivery damages trust more than ten excellent ones repair it.
