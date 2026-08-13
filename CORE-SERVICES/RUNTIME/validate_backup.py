from __future__ import annotations

import argparse
import sys
from pathlib import Path

from backup_restore_common import backup_dir_from_ref, validate_backup_set
from ops_common import DEFAULT_ENV_FILE, load_environment


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a canonical AI5R runtime backup set")
    parser.add_argument("backup_ref", type=str, help="Backup ID or explicit backup directory path")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    args = parser.parse_args()

    config = load_environment(args.env_file)
    backup_dir = backup_dir_from_ref(config, args.backup_ref)
    result = validate_backup_set(backup_dir)
    if not result.ok:
        for error in result.errors:
            print(f"[FAIL] {error}")
        return 1
    print(f"[PASS] backup valid: {backup_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
