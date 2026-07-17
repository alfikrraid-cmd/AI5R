**Knowledge ID:** MR-KR-001
**Title:** Attempt real execution wherever the environment genuinely allows it, even when other modules in the same order are blocked
**Source Manufacturing Order:** MO-001
**Source Manufacturing Review:** MR-001
**Evidence:** MO-001's Basic AI Assistant module had no external dependency (`AI5R-SDK/BRAIN`'s pipeline is pure Python). It was actually executed rather than only structurally checked, and this surfaced a real defect (`ValueError: Observation must have source_object_id`) that `bash -n`/JSON-validity checks would never have caught, because the defect was in how the module's own input was shaped, not in its syntax. Six other modules in the same order remained blocked on a missing database credential; this did not stop the one module that could be executed from actually being executed.
**Recommendation:** In every future Manufacturing Order, identify which modules have no external dependency and can genuinely be executed in the current environment, and actually run them — do not default to structural-validation-only across an entire order just because some modules are environment-blocked.
**Reuse Scope:** All future Manufacturing Orders, at the Verification phase.
