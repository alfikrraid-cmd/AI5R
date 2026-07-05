from datetime import datetime, timezone


class ManufacturingClock:
    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()
