from enum import Enum


class ArtifactStatus(str, Enum):
    DRAFT = "DRAFT"
    MANUFACTURED = "MANUFACTURED"
    REGISTERED = "REGISTERED"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"
