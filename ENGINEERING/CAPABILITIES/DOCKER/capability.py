import subprocess
from datetime import datetime, timezone

from ENGINEERING.RUNTIME.contracts import Capability, CapabilityRequest
from ENGINEERING.RUNTIME.result import CapabilityResult, CapabilityStatus

from .contracts import DockerRequest
from .exceptions import UnsupportedDockerOperation
from .models import OPERATION_MAP, SUPPORTED_OPERATIONS


class DockerCapability(Capability):
    capability_code = "docker"
    capability_name = "Docker Capability"
    capability_version = "1.0.0"
    capability_description = (
        "Executes read-only Docker engineering operations "
        "(version, container listing, image listing) via the Docker CLI."
    )
    SUPPORTED_OPERATIONS = SUPPORTED_OPERATIONS

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        started_at = datetime.now(timezone.utc)
        docker_request = DockerRequest(
            operation=request.payload.get("operation", ""),
            payload=request.payload,
        )

        try:
            if docker_request.operation not in SUPPORTED_OPERATIONS:
                raise UnsupportedDockerOperation(
                    f"Unsupported Docker operation: {docker_request.operation!r}"
                )

            command = OPERATION_MAP[docker_request.operation]
            completed = subprocess.run(command, capture_output=True, text=True)

            return self._build_result(
                status=(
                    CapabilityStatus.SUCCESS
                    if completed.returncode == 0
                    else CapabilityStatus.FAILED
                ),
                message=(
                    f"docker operation '{docker_request.operation}' "
                    f"exited with code {completed.returncode}"
                ),
                payload={
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                    "return_code": completed.returncode,
                },
                operation=docker_request.operation,
                command=command,
                started_at=started_at,
            )

        except UnsupportedDockerOperation as exc:
            return self._build_result(
                status=CapabilityStatus.FAILED,
                message=str(exc),
                payload={},
                operation=docker_request.operation,
                command=None,
                started_at=started_at,
            )

        except OSError as exc:
            return self._build_result(
                status=CapabilityStatus.FAILED,
                message=f"Failed to execute docker command: {exc}",
                payload={},
                operation=docker_request.operation,
                command=OPERATION_MAP.get(docker_request.operation),
                started_at=started_at,
            )

    def _build_result(
        self,
        status: CapabilityStatus,
        message: str,
        payload: dict,
        operation: str,
        command,
        started_at: datetime,
    ) -> CapabilityResult:
        finished_at = datetime.now(timezone.utc)

        return CapabilityResult(
            status=status,
            message=message,
            payload=payload,
            metadata={"operation": operation, "command": command},
            started_at=started_at,
            finished_at=finished_at,
            duration=(finished_at - started_at).total_seconds(),
        )
