from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from CORE.artifact_status import ArtifactStatus


@dataclass
class Artifact:

    artifact_type: str

    artifact_name: str

    artifact_id: str = field(
        default_factory=lambda: f"ART-{uuid4()}"
    )

    version: str = "1.0.0"

    status: ArtifactStatus = ArtifactStatus.DRAFT

    metadata: dict = field(default_factory=dict)

    created_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    updated_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    def manufacture(self):
        self.status = ArtifactStatus.MANUFACTURED

    def register(self):
        self.status = ArtifactStatus.REGISTERED

    def activate(self):
        self.status = ArtifactStatus.ACTIVE

    def deprecate(self):
        self.status = ArtifactStatus.DEPRECATED

    def archive(self):
        self.status = ArtifactStatus.ARCHIVED
