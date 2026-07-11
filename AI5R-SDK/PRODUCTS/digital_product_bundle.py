"""
MWO-006
Digital Product Bundle

Deterministic, stateless aggregator that combines Factory Pack artifact
dicts (website, api, docs, tests) into a single product bundle. Pure
aggregation only: no filesystem writes, no LLM, no reasoning, no
Organization / Manufacturing / Executive coupling.
"""

from __future__ import annotations

import copy
from typing import Any

BUNDLE_VERSION = "1.0"
SECTION_NAMES = ("website", "api", "docs", "tests")


class DigitalProductBundle:
    def bundle(self, product_name: Any, artifacts: Any) -> dict[str, Any]:
        if not isinstance(product_name, str) or not product_name.strip():
            raise ValueError("product_name is required")

        if not isinstance(artifacts, dict):
            raise ValueError("artifacts must be a dict")

        sections = {
            name: copy.deepcopy(artifacts.get(name) or {}) for name in SECTION_NAMES
        }

        manifest = {
            "product_name": product_name,
            "generated_at": None,
            "artifact_count": len(artifacts),
            "bundle_version": BUNDLE_VERSION,
        }

        return {
            "manifest.json": manifest,
            **sections,
        }
