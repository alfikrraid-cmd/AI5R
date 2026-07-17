# Docker Capability

The first production capability running on top of the Engineering Runtime
(`ENGINEERING/RUNTIME`). It implements `Capability` from
`ENGINEERING.RUNTIME.contracts` and requires zero changes to the Runtime,
Registry, Executor, or Policy.

## Supported Operations

Communication uses engineering operations, not CLI commands — the Docker
CLI is an implementation detail hidden inside this capability.

```
SUPPORTED_OPERATIONS = {
    "GET_VERSION",
    "LIST_CONTAINERS",
    "LIST_IMAGES",
}
```

| Operation          | Underlying command   |
|---------------------|----------------------|
| `GET_VERSION`       | `docker --version`   |
| `LIST_CONTAINERS`   | `docker ps`          |
| `LIST_IMAGES`       | `docker images`      |

Any other operation returns a `FAILED` `CapabilityResult` — it never raises
and never crashes the Runtime.

## Architecture

```
+-------------------------------------------------------------+
|                    EngineeringRuntime (unmodified)          |
|          Policy -> Registry -> Executor -> Capability       |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                     DockerCapability                        |
|                     (capability.py)                         |
|                                                               |
|  capability_code        = "docker"                          |
|  capability_name        = "Docker Capability"                |
|  capability_version     = "1.0.0"                             |
|  capability_description = "..."                              |
|  SUPPORTED_OPERATIONS   = {...}         (read-only metadata) |
|                                                               |
|  execute(request):                                           |
|    1. read request.payload["operation"]                      |
|    2. validate against SUPPORTED_OPERATIONS                  |
|    3. look up OPERATION_MAP[operation]                       |
|    4. subprocess.run(command, capture_output=True, text=True)|
|    5. return CapabilityResult (stdout, stderr, return_code)  |
+-------------------------------------------------------------+
        |                      |                    |
        v                      v                    v
  contracts.py            models.py           exceptions.py
  DockerRequest       SUPPORTED_OPERATIONS   UnsupportedDockerOperation
  (operation, payload)   OPERATION_MAP        (internal, always caught)
```

`CapabilityResult` is reused as-is from `ENGINEERING.RUNTIME.result` — no
duplicate result object exists.

Command execution always uses `subprocess.run` (never `os.system`), and
always captures `stdout`, `stderr`, and the return code. `started_at`,
`finished_at`, and `duration` are populated on every result, success or
failure.

## Example Request

```python
from ENGINEERING.RUNTIME.contracts import CapabilityRequest

CapabilityRequest(
    capability="docker",
    payload={"operation": "GET_VERSION"},
)
```

## Example Response

```python
CapabilityResult(
    status=CapabilityStatus.SUCCESS,
    message="docker operation 'GET_VERSION' exited with code 0",
    payload={
        "stdout": "Docker version 24.0.0, build ...\n",
        "stderr": "",
        "return_code": 0,
    },
    metadata={"operation": "GET_VERSION", "command": ["docker", "--version"]},
    started_at=...,
    finished_at=...,
    duration=0.031,
)
```

An unsupported operation:

```python
CapabilityRequest(capability="docker", payload={"operation": "DELETE_EVERYTHING"})

# ->

CapabilityResult(
    status=CapabilityStatus.FAILED,
    message="Unsupported Docker operation: 'DELETE_EVERYTHING'",
    payload={},
    ...
)
```

## Runtime Integration

`DockerCapability` plugs into the existing, unmodified Runtime exactly like
any other capability:

```python
from ENGINEERING.RUNTIME.contracts import CapabilityRequest
from ENGINEERING.RUNTIME.executor import CapabilityExecutor
from ENGINEERING.RUNTIME.policy import RuntimePolicy
from ENGINEERING.RUNTIME.registry import CapabilityRegistry
from ENGINEERING.RUNTIME.runtime import EngineeringRuntime

from ENGINEERING.CAPABILITIES.DOCKER.capability import DockerCapability

registry = CapabilityRegistry()
registry.register(DockerCapability())

policy = RuntimePolicy(allowed_capabilities=["docker"])
executor = CapabilityExecutor()
runtime = EngineeringRuntime(registry=registry, policy=policy, executor=executor)

result = runtime.execute(
    CapabilityRequest(capability="docker", payload={"operation": "GET_VERSION"})
)
```

No import from `ENGINEERING.RUNTIME` other than `contracts` (for
`Capability`/`CapabilityRequest`) and `result` (for
`CapabilityResult`/`CapabilityStatus`) is required — `runtime.py`,
`registry.py`, `executor.py`, and `policy.py` are used exactly as released,
unmodified.

## Running the Tests

```bash
python3 -m pytest ENGINEERING/CAPABILITIES/DOCKER/TESTS -q
```

Tests mock `subprocess.run` and do not require Docker to be installed.

## Running the Demo

```bash
python3 -m ENGINEERING.CAPABILITIES.DOCKER.demo
```

If Docker is not installed on the host, the demo still runs to completion
and prints a `FAILED` status with the underlying OS error captured in
`message` — it does not crash.
