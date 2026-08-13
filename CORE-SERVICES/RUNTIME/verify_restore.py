from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from ops_common import DEFAULT_COMPOSE_FILE, DEFAULT_ENV_FILE, load_environment, validate_environment


def run(command: list[str], *, dry_run: bool = False) -> int:
    print("+ " + " ".join(str(part) for part in command))
    if dry_run:
        return 0
    completed = subprocess.run(command, check=False)
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify that a production backup is restorable before cutover.")
    parser.add_argument("backup_ref", help="Backup id or backup directory accepted by validate_backup.py/restore.py.")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--compose-file", type=Path, default=DEFAULT_COMPOSE_FILE)
    parser.add_argument("--execute-restore", action="store_true", help="Actually run restore.py; destructive for the target runtime.")
    parser.add_argument("--allow-version-mismatch", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_environment(args.env_file)
    validation = validate_environment(config)
    if not validation.ok:
        for error in validation.errors:
            print(f"[FAIL] {error}")
        return 1

    validate_command = [
        sys.executable,
        str(Path(__file__).with_name("validate_backup.py")),
        args.backup_ref,
        "--env-file",
        str(args.env_file),
    ]
    code = run(validate_command, dry_run=args.dry_run)
    if code != 0:
        return code

    restore_command = [
        sys.executable,
        str(Path(__file__).with_name("restore.py")),
        args.backup_ref,
        "--env-file",
        str(args.env_file),
        "--compose-file",
        str(args.compose_file),
        "--yes",
    ]
    if args.allow_version_mismatch:
        restore_command.append("--allow-version-mismatch")

    if not args.execute_restore:
        print("[PASS] backup validation passed")
        print("[INFO] restore command prepared but not executed; pass --execute-restore in an approved restore target")
        print("+ " + " ".join(str(part) for part in restore_command))
        return 0

    code = run(restore_command, dry_run=args.dry_run)
    if code != 0:
        return code
    print("[PASS] restore verification completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())