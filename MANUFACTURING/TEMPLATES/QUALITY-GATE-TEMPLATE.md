# Quality Gate — <Module or Order Name>

Updated per MR-001 (Manufacturing Review of MO-001) — see `MANUFACTURING/MR-001/MR-001-MANUFACTURING-REVIEW.md` for the evidence this template is based on.

## Structural Validation (always required)

- [ ] Shell syntax (`bash -n`) — 0 errors
- [ ] JSON/schema validity — 0 invalid
- [ ] Language compile check (e.g. `py_compile`) if applicable — clean
- [ ] Scope check — only intended files touched (git status diff)

## Runtime Verification (required to attempt; outcome may legitimately be BLOCKER)

- [ ] Verifiability class stated: DB-dependent / external-service-dependent / self-contained
- [ ] Pre-flight environment check performed and recorded (credential present? service reachable?)
- [ ] If self-contained or environment-capable: actually executed, real output captured, PASS/FAIL stated
- [ ] If blocked: exact blocking condition named (not vague), and confirmed external to this order's own deliverables
- [ ] If a verification runner was used: confirm its output reached its own real completion marker before citing any pass/fail count from it (do not truncate verification output with pipes like `head`)

## Determination

- [ ] Structural Validation: PASS / WARNING / BLOCKER
- [ ] Runtime Verification: PASS / BLOCKER (with named reason) — never omitted, never implied
- [ ] Overall module status stated independently per module, not only as one order-wide roll-up
