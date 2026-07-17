import subprocess
from unittest.mock import patch

from ENGINEERING.RUNTIME.contracts import CapabilityRequest
from ENGINEERING.RUNTIME.executor import CapabilityExecutor
from ENGINEERING.RUNTIME.policy import RuntimePolicy
from ENGINEERING.RUNTIME.registry import CapabilityRegistry
from ENGINEERING.RUNTIME.result import CapabilityStatus
from ENGINEERING.RUNTIME.runtime import EngineeringRuntime

from ENGINEERING.CAPABILITIES.DOCKER.capability import DockerCapability


def make_completed_process(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=["docker"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_get_version_success():
    capability = DockerCapability()
    request = CapabilityRequest(capability="docker", payload={"operation": "GET_VERSION"})

    with patch("ENGINEERING.CAPABILITIES.DOCKER.capability.subprocess.run") as mock_run:
        mock_run.return_value = make_completed_process(
            returncode=0, stdout="Docker version 24.0.0\n"
        )

        result = capability.execute(request)

    mock_run.assert_called_once_with(
        ["docker", "--version"], capture_output=True, text=True
    )
    assert result.status == CapabilityStatus.SUCCESS
    assert result.payload["stdout"] == "Docker version 24.0.0\n"
    assert result.payload["return_code"] == 0
    assert result.started_at is not None
    assert result.finished_at is not None
    assert result.finished_at >= result.started_at
    assert result.duration >= 0


def test_list_containers_success():
    capability = DockerCapability()
    request = CapabilityRequest(capability="docker", payload={"operation": "LIST_CONTAINERS"})

    with patch("ENGINEERING.CAPABILITIES.DOCKER.capability.subprocess.run") as mock_run:
        mock_run.return_value = make_completed_process(returncode=0, stdout="CONTAINER ID\n")

        result = capability.execute(request)

    mock_run.assert_called_once_with(["docker", "ps"], capture_output=True, text=True)
    assert result.status == CapabilityStatus.SUCCESS
    assert result.started_at is not None
    assert result.finished_at is not None
    assert result.duration >= 0


def test_list_images_success():
    capability = DockerCapability()
    request = CapabilityRequest(capability="docker", payload={"operation": "LIST_IMAGES"})

    with patch("ENGINEERING.CAPABILITIES.DOCKER.capability.subprocess.run") as mock_run:
        mock_run.return_value = make_completed_process(returncode=0, stdout="REPOSITORY\n")

        result = capability.execute(request)

    mock_run.assert_called_once_with(["docker", "images"], capture_output=True, text=True)
    assert result.status == CapabilityStatus.SUCCESS
    assert result.started_at is not None
    assert result.finished_at is not None
    assert result.duration >= 0


def test_unsupported_operation_returns_failed_without_crashing():
    capability = DockerCapability()
    request = CapabilityRequest(capability="docker", payload={"operation": "DELETE_EVERYTHING"})

    with patch("ENGINEERING.CAPABILITIES.DOCKER.capability.subprocess.run") as mock_run:
        result = capability.execute(request)

    mock_run.assert_not_called()
    assert result.status == CapabilityStatus.FAILED
    assert "DELETE_EVERYTHING" in result.message
    assert result.started_at is not None
    assert result.finished_at is not None
    assert result.duration >= 0


def test_command_failure_returns_failed_with_stderr_captured():
    capability = DockerCapability()
    request = CapabilityRequest(capability="docker", payload={"operation": "GET_VERSION"})

    with patch("ENGINEERING.CAPABILITIES.DOCKER.capability.subprocess.run") as mock_run:
        mock_run.return_value = make_completed_process(
            returncode=1, stdout="", stderr="docker: command not found\n"
        )

        result = capability.execute(request)

    assert result.status == CapabilityStatus.FAILED
    assert result.payload["stderr"] == "docker: command not found\n"
    assert result.payload["return_code"] == 1
    assert result.started_at is not None
    assert result.finished_at is not None
    assert result.duration >= 0


def test_docker_not_installed_returns_failed_without_crashing():
    capability = DockerCapability()
    request = CapabilityRequest(capability="docker", payload={"operation": "GET_VERSION"})

    with patch("ENGINEERING.CAPABILITIES.DOCKER.capability.subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("docker: not found")

        result = capability.execute(request)

    assert result.status == CapabilityStatus.FAILED
    assert "Failed to execute docker command" in result.message
    assert result.started_at is not None
    assert result.finished_at is not None
    assert result.duration >= 0


def test_docker_capability_executes_through_runtime():
    registry = CapabilityRegistry()
    registry.register(DockerCapability())

    policy = RuntimePolicy(allowed_capabilities=["docker"])
    executor = CapabilityExecutor()
    runtime = EngineeringRuntime(registry=registry, policy=policy, executor=executor)

    request = CapabilityRequest(capability="docker", payload={"operation": "GET_VERSION"})

    with patch("ENGINEERING.CAPABILITIES.DOCKER.capability.subprocess.run") as mock_run:
        mock_run.return_value = make_completed_process(
            returncode=0, stdout="Docker version 24.0.0\n"
        )

        result = runtime.execute(request)

    assert result.status == CapabilityStatus.SUCCESS
    assert result.payload["stdout"] == "Docker version 24.0.0\n"
    assert result.started_at is not None
    assert result.finished_at is not None
    assert result.duration >= 0
