from datetime import datetime, UTC

from PROCESS_MANAGER import ProcessManager


class LifecycleManager:
    VALID_TRANSITIONS = {
        "RUNNING": {"PAUSED", "STOPPED"},
        "PAUSED": {"RUNNING", "STOPPED"},
        "STOPPED": set(),
    }

    def __init__(self, process_manager: ProcessManager):
        self.process_manager = process_manager

    def pause(self, process_id: str):
        process = self.process_manager.get(process_id)

        if process is None:
            return None

        self._transition(process, "PAUSED")
        return process

    def resume(self, process_id: str):
        process = self.process_manager.get(process_id)

        if process is None:
            return None

        self._transition(process, "RUNNING")
        return process

    def stop(self, process_id: str):
        process = self.process_manager.get(process_id)

        if process is None:
            return None

        self._transition(process, "STOPPED")
        return process

    def _transition(self, process, target_status):
        current = process.status

        if target_status not in self.VALID_TRANSITIONS.get(current, set()):
            raise ValueError(
                f"Invalid lifecycle transition: {current} -> {target_status}"
            )

        process.status = target_status
        process.payload.setdefault("lifecycle", []).append({
            "from": current,
            "to": target_status,
            "timestamp": datetime.now(UTC).isoformat(),
        })
