from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from ops_common import DEFAULT_COMPOSE_FILE, DEFAULT_ENV_FILE, compose_command, load_environment, validate_environment


@dataclass(slots=True)
class StageResult:
    name: str
    command: list[str]
    status: str
    started_at: str
    finished_at: str
    returncode: int
    output: str


def now() -> str:
    return datetime.now(UTC).isoformat()


def capture(command: list[str], *, dry_run: bool = False) -> StageResult:
    started_at = now()
    if dry_run:
        return StageResult(
            name="",
            command=command,
            status="DRY_RUN",
            started_at=started_at,
            finished_at=now(),
            returncode=0,
            output="dry run: command not executed",
        )

    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    output = ((completed.stdout or "") + (completed.stderr or "")).strip()
    return StageResult(
        name="",
        command=command,
        status="PASS" if completed.returncode == 0 else "FAIL",
        started_at=started_at,
        finished_at=now(),
        returncode=completed.returncode,
        output=output,
    )


def run_stage(name: str, command: list[str], *, dry_run: bool, evidence: list[StageResult]) -> StageResult:
    print(f"[STAGE] {name}")
    print("+ " + " ".join(str(part) for part in command))
    result = capture(command, dry_run=dry_run)
    result.name = name
    evidence.append(result)
    if result.output:
        print(result.output)
    print(f"[{result.status}] {name}")
    return result


def release_summary(config: dict[str, str], env_file: Path, compose_file: Path, stages: list[StageResult], status: str) -> dict[str, object]:
    compose_services = []
    compose_error = None
    compose_stage = next((stage for stage in stages if stage.name == "compose-config"), None)
    if compose_stage and compose_stage.status == "PASS" and compose_stage.returncode == 0 and compose_stage.output:
        compose_services = [line.strip() for line in compose_stage.output.splitlines() if line.strip()]
    elif compose_stage and compose_stage.status == "FAIL":
        compose_error = compose_stage.output

    return {
        "created_at": now(),
        "status": status,
        "env_file": str(env_file),
        "compose_file": str(compose_file),
        "ai5r_version": config.get("AI5R_VERSION"),
        "domain": config.get("AI5R_DOMAIN"),
        "image_tags": {
            "dashboard": f"{config.get('AI5R_DASHBOARD_IMAGE_REPO')}:{config.get('AI5R_VERSION')}",
            "api": f"{config.get('AI5R_API_IMAGE_REPO')}:{config.get('AI5R_VERSION')}",
            "postgres": config.get("AI5R_POSTGRES_IMAGE"),
            "redis": config.get("AI5R_REDIS_IMAGE"),
            "n8n": config.get("AI5R_N8N_IMAGE"),
            "minio": config.get("AI5R_MINIO_IMAGE"),
            "nginx": config.get("AI5R_NGINX_IMAGE"),
            "gotenberg": config.get("AI5R_GOTENBERG_IMAGE"),
            "neo4j": config.get("AI5R_NEO4J_IMAGE"),
        },
        "compose_services": compose_services,
        "compose_error": compose_error,
        "stages": [asdict(stage) for stage in stages],
        "manual_requirements": [
            "existing system nginx/certbot checked on host",
            "production secrets installed outside git",
            "backup completed before deploy unless --skip-backup was approved",
            "rollback target version known before release execution",
        ],
    }


def write_evidence(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the canonical AI5ROS production release flow.")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--compose-file", type=Path, default=DEFAULT_COMPOSE_FILE)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("RELEASE-CANDIDATE.json"))
    parser.add_argument("--rollback-version", help="Previously approved AI5R_VERSION/image tag for automatic rollback on failure.")
    parser.add_argument("--skip-backup", action="store_true")
    parser.add_argument("--pull", action="store_true", help="Ask deploy.py to pull pinned images before deploy.")
    parser.add_argument("--no-build", action="store_true", help="Ask deploy.py not to build application images.")
    parser.add_argument("--smoke-base-url", default=None, help="Override public gateway URL for smoke_test.py.")
    parser.add_argument(
        "--start-at",
        choices=("compose-config", "backup", "deploy", "healthcheck", "smoke"),
        default="compose-config",
        help="Resume from this stage after validate-env.",
    )
    parser.add_argument(
        "--stop-after",
        choices=("compose-config", "backup", "deploy", "healthcheck", "smoke"),
        default=None,
        help="Stop after this stage and write evidence.",
    )
    parser.add_argument("--rollback-dry-run", action="store_true", help="Run rollback.py with --dry-run if rollback is triggered.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_environment(args.env_file)
    validation = validate_environment(config)
    stages: list[StageResult] = []

    validate_status = "PASS" if validation.ok else "FAIL"
    stages.append(
        StageResult(
            name="validate-env",
            command=[sys.executable, str(Path(__file__).with_name("validate_config.py")), "--env-file", str(args.env_file)],
            status=validate_status,
            started_at=now(),
            finished_at=now(),
            returncode=0 if validation.ok else 1,
            output="\n".join(validation.errors) if validation.errors else "configuration valid",
        )
    )
    if not validation.ok:
        payload = release_summary(config, args.env_file, args.compose_file, stages, "BLOCKED")
        write_evidence(args.output, payload)
        return 1

    flow_failed = False
    failed_stage = None
    stopped_after = None
    stage_order = ("compose-config", "backup", "deploy", "healthcheck", "smoke")
    active = False

    for stage_name in stage_order:
        if stage_name == args.start_at:
            active = True
        if not active:
            stages.append(
                StageResult(
                    name=stage_name,
                    command=[],
                    status="SKIPPED",
                    started_at=now(),
                    finished_at=now(),
                    returncode=0,
                    output=f"skipped by --start-at {args.start_at}",
                )
            )
            continue

        if stage_name == "backup" and args.skip_backup:
            result = StageResult(
                name="backup",
                command=[],
                status="SKIPPED",
                started_at=now(),
                finished_at=now(),
                returncode=0,
                output="backup skipped by --skip-backup",
            )
            stages.append(result)
        elif stage_name == "compose-config":
            result = run_stage(stage_name, compose_command(args.env_file, args.compose_file, "config", "--services"), dry_run=args.dry_run, evidence=stages)
        elif stage_name == "backup":
            result = run_stage(
                stage_name,
                [sys.executable, str(Path(__file__).with_name("backup.py")), "--env-file", str(args.env_file), "--compose-file", str(args.compose_file)],
                dry_run=args.dry_run,
                evidence=stages,
            )
        elif stage_name == "deploy":
            deploy_command = [
                sys.executable,
                str(Path(__file__).with_name("deploy.py")),
                "--env-file",
                str(args.env_file),
                "--compose-file",
                str(args.compose_file),
                "--skip-backup",
            ]
            if args.pull:
                deploy_command.append("--pull")
            if args.no_build:
                deploy_command.append("--no-build")
            if args.dry_run:
                deploy_command.append("--dry-run")
            result = run_stage(stage_name, deploy_command, dry_run=False, evidence=stages)
        elif stage_name == "healthcheck":
            result = run_stage(
                stage_name,
                [sys.executable, str(Path(__file__).with_name("healthcheck.py")), "--env-file", str(args.env_file), "--compose-file", str(args.compose_file)],
                dry_run=args.dry_run,
                evidence=stages,
            )
        else:
            smoke_command = [sys.executable, str(Path(__file__).with_name("smoke_test.py")), "--env-file", str(args.env_file)]
            if args.smoke_base_url:
                smoke_command.extend(["--base-url", args.smoke_base_url])
            result = run_stage(stage_name, smoke_command, dry_run=args.dry_run, evidence=stages)

        if result.returncode != 0:
            flow_failed = True
            failed_stage = stage_name
            break
        if args.stop_after == stage_name:
            stopped_after = stage_name
            break

    if flow_failed and args.rollback_version:
        rollback_command = [
            sys.executable,
            str(Path(__file__).with_name("rollback.py")),
            "--env-file",
            str(args.env_file),
            "--compose-file",
            str(args.compose_file),
            "--target-version",
            args.rollback_version,
            "--skip-backup",
        ]
        if args.dry_run or args.rollback_dry_run:
            rollback_command.append("--dry-run")
        run_stage("rollback", rollback_command, dry_run=False, evidence=stages)
    elif flow_failed:
        stages.append(
            StageResult(
                name="rollback",
                command=[],
                status="SKIPPED",
                started_at=now(),
                finished_at=now(),
                returncode=0,
                output="rollback skipped: --rollback-version was not provided",
            )
        )

    if args.dry_run:
        status = "DRY_RUN"
    elif stopped_after:
        status = "PARTIAL"
    else:
        status = "RELEASED" if not flow_failed else "ROLLED_BACK" if args.rollback_version else "FAILED"

    stages.append(
        StageResult(
            name="release-evidence",
            command=["write", str(args.output)],
            status="PASS",
            started_at=now(),
            finished_at=now(),
            returncode=0,
            output=f"release evidence written with status {status}",
        )
    )
    payload = release_summary(config, args.env_file, args.compose_file, stages, status)
    if failed_stage:
        payload["failed_stage"] = failed_stage
    if stopped_after:
        payload["stopped_after"] = stopped_after
    write_evidence(args.output, payload)
    return 0 if status in {"RELEASED", "DRY_RUN", "PARTIAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())