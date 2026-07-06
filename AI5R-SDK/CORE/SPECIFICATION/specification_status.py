from enum import Enum


class SpecificationStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    FROZEN = "FROZEN"
    DEPRECATED = "DEPRECATED"
