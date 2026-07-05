from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class KernelContext:

    kernel_id: str

    user_input: str

    identity_context: dict[str, Any] = field(default_factory=dict)

    position_context: dict[str, Any] = field(default_factory=dict)

    decision_context: dict[str, Any] = field(default_factory=dict)

    execution_context: dict[str, Any] = field(default_factory=dict)

    metadata: dict[str, Any] = field(default_factory=dict)

    object_type: str = "KERNEL_CONTEXT"

    status: str = "CREATED"

    context_id: str = field(
        default_factory=lambda: f"KCTX-{uuid4()}"
    )
