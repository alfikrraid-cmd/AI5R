from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from ops_common import DEFAULT_COMPOSE_FILE, DEFAULT_ENV_FILE, compose_command, load_environment, validate_environment


def run(command: list[str], *, dry_run: bool = False) -> int:
    print("+ " + " ".join(str(part) for part in command))
    if dry_run:
        return 0
    completed = subprocess.run(command, check=False)
    return completed.returncode


def run_required(command: list[str], *, dry_run: bool = False) -> None:
    code = run(command, dry_run=dry_run)
    if code != 0:
        raise SystemExit(code)


def main() -> int:
    parser = argparse.ArgumentParser(description="AI5ROS production rollback wrapper for the canonical runtime.")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--compose-file", type=Path, default=DEFAULT_COMPOSE_FILE)
    parser.add_argument("--target-version", required=True, help="Previously approved AI5R_VERSION/image tag to redeploy.")
    parser.add_argument("--skip-backup", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_environment(args.env_file)
    validation = validate_environment(config)
    if not validation.ok:
        for error in validation.errors:
            print(f"[FAIL] {error}")
        return 1

    if not args.skip_backup:
        run_required(
            [sys.executable, str(Path(__file__).with_name("backup.py")), "--env-file", str(args.env_file), "--compose-file", str(args.compose_file)],
            dry_run=args.dry_run,
        )

    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    env["AI5R_VERSION"] = args.target_version
    command = compose_command(args.env_file, args.compose_file, "up", "-d", "--build")
    print("+ AI5R_VERSION=" + args.target_version + " " + " ".join(command))
    if not args.dry_run:
        completed = subprocess.run(command, check=False, env=env)
        if completed.returncode != 0:
            return completed.returncode

    run_required(
        [sys.executable, str(Path(__file__).with_name("healthcheck.py")), "--env-file", str(args.env_file), "--compose-file", str(args.compose_file)],
        dry_run=args.dry_run,
    )
    print("[PASS] production rollback sequence completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())