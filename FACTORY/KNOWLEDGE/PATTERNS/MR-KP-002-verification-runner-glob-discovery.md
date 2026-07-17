**Knowledge ID:** MR-KP-002
**Title:** Glob-based test discovery in the verification runner requires no maintenance as new modules are added
**Source Manufacturing Order:** MO-001
**Source Manufacturing Review:** MR-001
**Evidence:** `PRODUCTS/LTSA-BRAIN/VERIFICATION/run_verification.sh` discovers test scripts via `find "$PRODUCT_ROOT/BUILD-PACKS" -type f -name "*_test.sh"` with no hardcoded list (built under MWO-P-006). MO-001 added 21 new test scripts across 5 new modules, and the runner absorbed all of them with zero modification, confirmed by direct read of the script before manufacturing began.
**Recommendation:** Any future verification or discovery tooling built for this Factory should follow the same glob-based, no-hardcoded-list convention, so it does not require maintenance every time a new module is manufactured.
**Reuse Scope:** Any future test/verification runner across any AI5R product.
