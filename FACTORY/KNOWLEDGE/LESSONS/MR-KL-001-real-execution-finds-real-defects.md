**Knowledge ID:** MR-KL-001
**Title:** Real execution finds real defects that structural review cannot
**Source Manufacturing Order:** MO-001
**Source Manufacturing Review:** MR-001
**Evidence:** The Basic AI Assistant module passed `bash -n`-equivalent scrutiny (Python compiles cleanly, `py_compile` clean) but failed on first real execution with `ValueError: Observation must have source_object_id`, raised by unmodified `AI5R-SDK/BRAIN/understanding_engine.py`. The defect was in the shape of the input this module constructed, invisible to any static check performed, and was found only by actually running the code.
**Recommendation:** Treat structural validation as necessary but never sufficient evidence of correctness. Wherever real execution is possible, perform it, specifically because it finds a different class of defect than static checks do.
**Reuse Scope:** All future Manufacturing Orders, especially any module consuming another Factory asset's (BRAIN, Capability, Knowledge) real interface for the first time.
