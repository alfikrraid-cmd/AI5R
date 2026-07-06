from __future__ import annotations

from .runtime_snapshot import RuntimeSnapshot


class PersistentRuntime:
    def __init__(self):
        self._snapshots: dict[str, RuntimeSnapshot] = {}
        self._runtime_index: dict[str, list[str]] = {}

    def save(
        self,
        runtime_id: str,
        state: dict,
    ) -> RuntimeSnapshot:

        snapshot = RuntimeSnapshot(
            runtime_id=runtime_id,
            state=state,
        )

        self._snapshots[snapshot.snapshot_id] = snapshot
        self._runtime_index.setdefault(runtime_id, []).append(
            snapshot.snapshot_id
        )

        return snapshot

    def get_snapshot(
        self,
        snapshot_id: str,
    ):
        return self._snapshots.get(snapshot_id)

    def latest(
        self,
        runtime_id: str,
    ):
        ids = self._runtime_index.get(runtime_id, [])

        if not ids:
            return None

        return self._snapshots[ids[-1]]

    def history(
        self,
        runtime_id: str,
    ):
        return [
            self._snapshots[sid]
            for sid in self._runtime_index.get(runtime_id, [])
        ]

    def snapshot(self):
        return {
            sid: snap.snapshot()
            for sid, snap in self._snapshots.items()
        }
