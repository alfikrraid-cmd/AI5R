from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class CanonicalIdentity:
    prefix: str
    value: str


class CanonicalIdentityGenerator:

    _counters: dict[str, int] = {}

    @classmethod
    def generate(cls, prefix: str) -> CanonicalIdentity:
        if not prefix:
            raise ValueError("prefix is required")

        prefix = prefix.upper()

        cls._counters.setdefault(prefix, 0)
        cls._counters[prefix] += 1

        date = datetime.now(UTC).strftime("%Y%m%d")

        value = (
            f"AI5R-"
            f"{prefix}-"
            f"{date}-"
            f"{cls._counters[prefix]:08d}"
        )

        return CanonicalIdentity(
            prefix=prefix,
            value=value,
        )

    @classmethod
    def reset(cls):
        cls._counters.clear()

    @classmethod
    def current_counter(cls, prefix: str) -> int:
        return cls._counters.get(prefix.upper(), 0)
