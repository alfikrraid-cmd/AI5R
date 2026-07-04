from datetime import datetime
from uuid import uuid4


class RealityIntakeStation:
    """
    LTSA-004 Reality Intake Station

    Converts raw external input into a canonical Reality Enterprise Object.
    """

    def ingest(self, source_type, source_name, raw_content, metadata=None):
        if not source_type:
            raise ValueError("source_type is required")

        if not source_name:
            raise ValueError("source_name is required")

        if raw_content is None or raw_content == "":
            raise ValueError("raw_content is required")

        return {
            "id": str(uuid4()),
            "object_type": "reality",
            "station": "reality_intake",
            "source_type": source_type,
            "source_name": source_name,
            "raw_content": raw_content,
            "metadata": metadata or {},
            "status": "ingested",
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
