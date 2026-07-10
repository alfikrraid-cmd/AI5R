from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ManufacturingPayloadMerger:
    def merge(
        self,
        *,
        base: dict[str, Any],
        results: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        merged = dict(base)
        writes: dict[str, tuple[str, Any]] = {}

        for capability_id in sorted(results):
            output = results[capability_id]

            if not isinstance(output, dict):
                raise TypeError(
                    f"output for capability {capability_id!r} "
                    "must be a dictionary"
                )

            for key, value in output.items():
                if key == "artifacts":
                    merged["artifacts"] = self._merge_artifacts(
                        merged.get("artifacts"),
                        value,
                    )
                    continue

                # Capability handlers commonly return the full input
                # payload. Unchanged values are echoes, not writes.
                if key in base and base[key] == value:
                    continue

                previous_write = writes.get(key)

                if (
                    previous_write is not None
                    and previous_write[1] != value
                ):
                    previous_capability, previous_value = previous_write

                    raise ValueError(
                        f"payload conflict for key {key!r}: "
                        f"{previous_capability!r} wrote "
                        f"{previous_value!r}, while "
                        f"{capability_id!r} wrote {value!r}"
                    )

                writes[key] = (capability_id, value)

        for key, (_, value) in writes.items():
            merged[key] = value

        return merged

    @staticmethod
    def _merge_artifacts(
        current: Any,
        incoming: Any,
    ) -> list[str]:
        artifacts: list[str] = []

        def append_values(value: Any) -> None:
            if value is None:
                return

            if isinstance(value, str):
                candidates = (value,)
            elif isinstance(value, (list, tuple)):
                candidates = tuple(value)
            else:
                raise TypeError(
                    "artifacts must be a string, list, or tuple"
                )

            for candidate in candidates:
                if not isinstance(candidate, str):
                    raise TypeError(
                        "artifact entries must be strings"
                    )

                trimmed = candidate.strip()

                if trimmed and trimmed not in artifacts:
                    artifacts.append(trimmed)

        append_values(current)
        append_values(incoming)

        return artifacts
