from dataclasses import dataclass


@dataclass(frozen=True)
class ImportError(Exception):
    code: str
    message: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "args", (self.message,))

    def __str__(self) -> str:
        return self.message


__all__ = ["ImportError"]
