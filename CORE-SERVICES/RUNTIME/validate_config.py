from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ops_common import DEFAULT_ENV_FILE, load_environment, validate_environment


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AI5R runtime operations configuration.")
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
        help="Environment file to validate.",
    )
    args = parser.parse_args()

    config = load_environment(args.env_file)
    result = validate_environment(config)

    if result.ok:
        print(f"[PASS] configuration valid: {args.env_file}")
        return 0

    for error in result.errors:
        print(f"[FAIL] {error}")

    for warning in result.warnings:
        print(f"[WARN] {warning}")

    return 1


if __name__ == "__main__":
    sys.exit(main())
