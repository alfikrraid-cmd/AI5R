**Knowledge ID:** MR-KQ-003
**Title:** Confirm a verification runner reached its own real completion marker before citing its result
**Source Manufacturing Order:** MO-001
**Source Manufacturing Review:** MR-001
**Evidence:** The `| head -100` incident in MO-001 (see MR-KR-004) produced output that looked plausible but had not reached `run_verification.sh`'s own `=== Verification Summary ===` marker. Only noticing the missing marker revealed the run was incomplete.
**Recommendation:** Before citing any pass/fail/skip count from a verification runner, confirm its output contains the runner's own stated completion marker. Treat its absence as "run incomplete or truncated," never as "zero issues found."
**Reuse Scope:** All future Manufacturing Orders using `VERIFICATION/run_verification.sh` or any equivalent future runner. Reflected in `MANUFACTURING/TEMPLATES/QUALITY-GATE-TEMPLATE.md`.
