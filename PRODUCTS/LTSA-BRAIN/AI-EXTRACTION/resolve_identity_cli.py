"""CLI wrapper reusing PumpIdentityResolver / SealIdentityResolver
(PUMP-FACTORY-PACK / SEAL-FACTORY-PACK) unmodified, so the LTSA n8n Document
Save workflow can resolve reviewed extraction fields against the existing
Pump / Seal registries without reimplementing any matching logic.

Both resolvers accept their `context` argument only to satisfy the
FACTORY.RESOLUTION.IdentityResolver interface -- neither reads it -- so this
wrapper passes None rather than constructing a real ManufacturingContext.

Usage:
    echo '{"candidate_key": {"tag_number": "P-101"}, "known": [...]}' | \
        python resolve_identity_cli.py --object-type PUMP

Prints {"matched": bool, "canonical_id": str|null, "confidence": float|null}
to stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SEAL_FACTORY_PACK = Path(__file__).resolve().parents[1] / "SEAL-FACTORY-PACK"
_PUMP_FACTORY_PACK = Path(__file__).resolve().parents[1] / "PUMP-FACTORY-PACK"
# Known finding (not fixed here, out of scope for this MWO): pump_identity_resolver.py
# and seal_identity_resolver.py each compute their own AI5R-SDK path one level too
# shallow (parents[2] resolves to PRODUCTS/AI5R-SDK, which does not exist, instead of
# the real repo-root AI5R-SDK). That stale sys.path entry is harmless -- Python skips
# a nonexistent directory when searching -- as long as the correct path is also on
# sys.path before those modules are imported, which this line ensures.
_AI5R_SDK_PATH = Path(__file__).resolve().parents[3] / "AI5R-SDK"
for _p in (_SEAL_FACTORY_PACK, _PUMP_FACTORY_PACK, _AI5R_SDK_PATH):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _resolver_for(object_type: str, known: list[dict]):
    if object_type == "PUMP":
        from pump_identity_resolver import PumpIdentityResolver

        return PumpIdentityResolver(known_pumps=known)
    if object_type == "SEAL":
        from seal_identity_resolver import SealIdentityResolver

        return SealIdentityResolver(known_seals=known)
    raise ValueError(f"Unsupported object_type: {object_type!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Identity resolution CLI wrapper")
    parser.add_argument("--object-type", required=True, choices=["PUMP", "SEAL"])
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    payload = json.loads(sys.stdin.read())
    candidate_key = payload["candidate_key"]
    known = payload.get("known", [])

    resolver = _resolver_for(args.object_type, known)
    resolution = resolver.resolve(args.object_type, candidate_key, context=None)

    print(json.dumps({
        "matched": resolution.matched,
        "canonical_id": resolution.canonical_id,
        "confidence": resolution.confidence,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
