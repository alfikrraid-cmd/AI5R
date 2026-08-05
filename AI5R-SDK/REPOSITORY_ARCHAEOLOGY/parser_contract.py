"""
MWO-RAE-000D -- ParserContract: the abstract contract every Repository
Archaeology parser implements. Mirrors ENTERPRISE_DATA_ENGINE.reader's
own Reader(ABC) shape (supports()/read()) -- stdlib-only, no parsing
logic of its own. A concrete implementation (PythonParser, MarkdownParser,
etc.) is explicitly out of scope for this MWO.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class ParserContract(ABC):
    """Stateless contract for a Repository Archaeology parser."""

    __slots__ = ()

    @abstractmethod
    def supports(self, path: Path) -> bool:
        """Return whether this parser can parse the given file."""

    @abstractmethod
    def parse(self, path: Path) -> Any:
        """Parse the given file and return its result."""


__all__ = ["ParserContract"]
