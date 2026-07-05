from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ArchitectureLayer:
    code: str
    name: str
    responsibilities: List[str]


class CanonicalCognitiveArchitecture:
    """
    Canonical architecture for AI5R.
    This class is the single source of truth for all cognitive layers.
    """

    LAYERS = [
        ArchitectureLayer(
            "ENT",
            "Enterprise",
            [
                "vision",
                "mission",
                "governance",
                "organization",
            ],
        ),
        ArchitectureLayer(
            "REA",
            "Reality",
            [
                "observation",
                "reality intake",
            ],
        ),
        ArchitectureLayer(
            "MFG",
            "Manufacturing",
            [
                "stations",
                "pipeline",
                "factory orchestration",
            ],
        ),
        ArchitectureLayer(
            "MEM",
            "Memory",
            [
                "warehouse",
                "experience",
                "memory",
            ],
        ),
        ArchitectureLayer(
            "KNW",
            "Knowledge",
            [
                "extraction",
                "classification",
                "prioritization",
                "relationship",
                "conflict detection",
                "graph",
            ],
        ),
        ArchitectureLayer(
            "COG",
            "Cognition",
            [
                "reasoning",
                "planning",
                "reflection",
            ],
        ),
        ArchitectureLayer(
            "DEC",
            "Decision",
            [
                "decision",
                "recommendation",
                "evaluation",
            ],
        ),
        ArchitectureLayer(
            "EXE",
            "Execution",
            [
                "action",
                "workflow",
                "integration",
            ],
        ),
        ArchitectureLayer(
            "LRN",
            "Learning",
            [
                "feedback",
                "innovation",
                "continuous improvement",
            ],
        ),
    ]

    @classmethod
    def all_layers(cls):
        return cls.LAYERS

    @classmethod
    def layer_codes(cls):
        return [layer.code for layer in cls.LAYERS]

    @classmethod
    def layer_names(cls):
        return [layer.name for layer in cls.LAYERS]

    @classmethod
    def find(cls, code: str):
        for layer in cls.LAYERS:
            if layer.code == code:
                return layer
        return None
