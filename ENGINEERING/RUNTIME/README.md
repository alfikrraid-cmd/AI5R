# Engineering Runtime Core

`ENGINEERING/RUNTIME` is the vendor-agnostic execution core for engineering
capabilities. It knows how to receive a request, validate it against policy,
look up a capability, execute it, and return a standardized result. It does
not know — and must never know — how any individual capability is
implemented (Docker, Git, SSH, filesystem, MCP, or otherwise).

The Runtime is intentionally small. It is not an async runtime, not a
dependency injection container, not middleware, not a plugin framework, not
a workflow engine, not a task scheduler, and not a service locator.

## Architecture

```
+----------------------------------------------------------------+
|                       EngineeringRuntime                       |
|                                                                  |
|   +--------------+   +--------------------+   +---------------+ |
|   | RuntimePolicy|   | CapabilityRegistry |   |CapabilityExec.| |
|   | (policy.py)  |   | (registry.py)      |   |(executor.py)  | |
|   |              |   |                    |   |               | |
|   | validate()   |   | register()         |   | execute()     | |
|   |              |   | unregister()       |   |               | |
|   |              |   | get()              |   |               | |
|   |              |   | list()             |   |               | |
|   |              |   | load_builtin()  *  |   |               | |
|   |              |   | load_package()  *  |   |               | |
|   +--------------+   +--------------------+   +---------------+ |
+----------------------------------------------------------------+
                              |
                              v
                 +-------------------------+
                 |   Capability (ABC)      |
                 |   contracts.py          |
                 |                         |
                 |   execute(request)      |
                 |   -> CapabilityResult   |
                 +-------------------------+

  * = reserved extension point, raises NotImplementedError
```

Supporting types:

```
contracts.py   -> CapabilityRequest, Capability (ABC)
result.py      -> CapabilityResult, CapabilityStatus
exceptions.py  -> CapabilityNotFound, PolicyViolation, RuntimeExecutionError
```

The Runtime contains no Docker, Git, SSH, filesystem, or MCP logic. Adapters
implementing those concerns live outside this package and plug in only
through the `Capability` contract.

## Request Flow

```
                 CapabilityRequest
                        |
                        v
              +--------------------+
              |  _before_execute() |   (hook, no-op by default)
              +--------------------+
                        |
                        v
              Policy.validate(request)  ------> raises PolicyViolation
                        |
                        v
              Registry.get(request.capability) -> raises CapabilityNotFound
                        |
                        v
              Executor.execute(capability, request)
                        |
                        v
              Capability.execute(request)
                        |
                        v
              +--------------------+
              |  _after_execute()  |   (hook, no-op by default)
              +--------------------+
                        |
                        v
                 CapabilityResult
```

`EngineeringRuntime.execute()` performs exactly these steps and returns
whatever `CapabilityResult` the capability produced. It does not catch,
interpret, or transform capability-level errors beyond what policy/registry
lookups themselves raise.

## Registry

`CapabilityRegistry` is a simple in-memory map from `capability_code` to a
registered `Capability` instance.

```python
registry = CapabilityRegistry()
registry.register(DockerCapability())
registry.register(GitCapability())

capability = registry.get("docker")
registry.unregister("docker")
all_capabilities = registry.list()
```

Looking up or unregistering a capability that was never registered raises
`CapabilityNotFound`.

## Executor

`CapabilityExecutor` is a pure pass-through:

```python
class CapabilityExecutor:
    def execute(self, capability, request):
        return capability.execute(request)
```

It carries no retry logic, no error translation, no side effects. Any such
behavior belongs inside a specific `Capability` implementation, not the
executor.

## Policy

`RuntimePolicy` is a dataclass with the minimum configuration required to
gate execution:

```python
policy = RuntimePolicy(
    allowed_capabilities=["hello", "docker"],
    readonly=False,
    dry_run=False,
)

policy.validate(request)  # raises PolicyViolation if request.capability
                           # is not in allowed_capabilities
```

`readonly` and `dry_run` are policy-level flags available for capabilities
and callers to consult; enforcing their semantics beyond capability
allow-listing is the responsibility of individual capabilities, since the
Runtime has no knowledge of what a capability actually does.

## Capability

`Capability` is the only contract a capability must satisfy:

```python
class Capability(ABC):
    capability_code: str
    capability_name: str

    @abstractmethod
    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        ...
```

`CapabilityRequest` carries the call:

```python
@dataclass
class CapabilityRequest:
    capability: str
    payload: dict
    metadata: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)  # reserved, see below
```

## Result

Every capability returns a `CapabilityResult`:

```python
@dataclass
class CapabilityResult:
    status: CapabilityStatus       # SUCCESS | FAILED | CANCELLED
    message: str
    payload: dict
    metadata: dict
    started_at: datetime | None
    finished_at: datetime | None
    duration: float
```

`CapabilityStatus` is a dedicated `Enum` (`SUCCESS`, `FAILED`, `CANCELLED`)
used consistently across the Runtime — no ad-hoc string statuses.
`CapabilityResult.success(...)` / `CapabilityResult.failure(...)` are
convenience constructors that fill in timing fields automatically.

## Runtime Hooks

`EngineeringRuntime` exposes two protected hook methods, called around every
`execute()` call:

```python
def _before_execute(self) -> None: ...   # no-op by default
def _after_execute(self) -> None: ...    # no-op by default
```

They exist only as extension points for future telemetry, auditing, and
metrics. They currently do nothing, take no arguments, and must not be
relied upon for any behavior today. Subclass `EngineeringRuntime` and
override them if a future capability needs to observe the execution
boundary.

## Future Extension Points

The following are reserved but intentionally unimplemented in this release:

```
CapabilityRequest.context     -> reserved dict for workspace, user,
                                  correlation id, runtime metadata.
                                  Not read by any runtime logic yet.

CapabilityRegistry.load_builtin()  -> raises NotImplementedError
CapabilityRegistry.load_package()  -> raises NotImplementedError
                                  Reserved for future capability discovery.
                                  No automatic discovery is implemented.

EngineeringRuntime._before_execute()
EngineeringRuntime._after_execute()
                                  Reserved for future telemetry/auditing.
```

None of these introduce new architecture. They are placeholders only, kept
deliberately empty so the Runtime stays small.

## Example Usage

```python
from ENGINEERING.RUNTIME.contracts import Capability, CapabilityRequest
from ENGINEERING.RUNTIME.result import CapabilityResult
from ENGINEERING.RUNTIME.registry import CapabilityRegistry
from ENGINEERING.RUNTIME.policy import RuntimePolicy
from ENGINEERING.RUNTIME.executor import CapabilityExecutor
from ENGINEERING.RUNTIME.runtime import EngineeringRuntime


class HelloCapability(Capability):
    capability_code = "hello"
    capability_name = "Hello Capability"

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        return CapabilityResult.success(message="hello")


registry = CapabilityRegistry()
registry.register(HelloCapability())

policy = RuntimePolicy(allowed_capabilities=["hello"])
executor = CapabilityExecutor()

runtime = EngineeringRuntime(registry=registry, policy=policy, executor=executor)

result = runtime.execute(CapabilityRequest(capability="hello", payload={}))

print(result.status)   # CapabilityStatus.SUCCESS
print(result.message)  # "hello"
```

## Running the Tests

```bash
python3 -m pytest ENGINEERING/RUNTIME/TESTS -q
```
