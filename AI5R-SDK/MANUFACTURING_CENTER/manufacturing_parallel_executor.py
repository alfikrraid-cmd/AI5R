from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Any


CapabilityRunner = Callable[[str], Any]


@dataclass(slots=True)
class ManufacturingParallelExecutor:
    max_workers: int | None = None

    def execute_level(
        self,
        capability_ids: tuple[str, ...],
        runner: CapabilityRunner,
    ) -> dict[str, Any]:
        if not capability_ids:
            return {}

        with ThreadPoolExecutor(
            max_workers=self.max_workers or len(capability_ids)
        ) as executor:
            futures = {
                capability: executor.submit(runner, capability)
                for capability in capability_ids
            }

            return {
                capability: future.result()
                for capability, future in futures.items()
            }
