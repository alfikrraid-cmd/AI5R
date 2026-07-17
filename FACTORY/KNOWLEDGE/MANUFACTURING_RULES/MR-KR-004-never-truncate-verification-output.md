**Knowledge ID:** MR-KR-004
**Title:** Never pipe a verification runner's output through a line-limiting filter when its completeness or exit code will be cited
**Source Manufacturing Order:** MO-001
**Source Manufacturing Review:** MR-001
**Evidence:** During MO-001, `VERIFICATION/run_verification.sh`'s output was piped through `| head -100` for readability. This caused the pipeline to report a misleadingly "complete-looking" but actually cut-off transcript (the run was terminated mid-execution once `head` had read enough lines), and the exit code observed did not reflect the underlying script's real outcome. The full run had to be re-launched from scratch, redirected to a file, and read in full, to obtain an honest transcript.
**Recommendation:** When a command's output will be cited as evidence (pass/fail counts, completion status), always redirect to a file and read it in full, or use an unlimited read, rather than piping through `head`/`tail -n` for convenience. Confirm the output contains the tool's own real completion marker (e.g. `=== Verification Summary ===`) before citing any count from it.
**Reuse Scope:** All future Manufacturing Orders and any engineering task citing a long-running verification command's output. Already reflected in `MANUFACTURING/TEMPLATES/QUALITY-GATE-TEMPLATE.md`.
