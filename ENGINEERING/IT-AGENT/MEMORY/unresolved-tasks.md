# Unresolved Tasks

Open threads the IT agent surfaced but did not resolve — needs a human
decision, more evidence, or is out of this layer's authorized scope
(e.g. anything hitting the hard-safety boundaries).

<!-- Format:
## YYYY-MM-DD — <short title>
What's blocking: ...
Needed: ...
-->

## 2026-08-29 — Decouple Fleet Reliability tiles from Power BI fetch gate
What's blocking: Needs an MWO + human product decision (should the two
optional fetches render independently, and should a failure surface any
visible state instead of silently omitting the section?) before any code
change — out of scope for a diagnosis-only mock task.
Needed: Product owner sign-off on desired behavior, then a small MWO.
