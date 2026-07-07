from __future__ import annotations

from dataclasses import asdict
from typing import Any

from OSA.STUDIO_LIVE_OPS import StudioLiveOpsSnapshot


class StudioAPIAdapter:
    def serialize_snapshot(
        self,
        snapshot: StudioLiveOpsSnapshot,
    ) -> dict[str, Any]:
        if snapshot is None:
            raise ValueError("snapshot is required")

        return {
            "type": "AI5R_STUDIO_LIVE_OPS_SNAPSHOT",
            "version": "1.0",
            "data": asdict(snapshot),
        }

    def serialize_many(
        self,
        snapshots: list[StudioLiveOpsSnapshot],
    ) -> dict[str, Any]:
        if snapshots is None:
            raise ValueError("snapshots is required")

        return {
            "type": "AI5R_STUDIO_LIVE_OPS_SNAPSHOT_LIST",
            "version": "1.0",
            "count": len(snapshots),
            "data": [
                self.serialize_snapshot(snapshot)["data"]
                for snapshot in snapshots
            ],
        }
