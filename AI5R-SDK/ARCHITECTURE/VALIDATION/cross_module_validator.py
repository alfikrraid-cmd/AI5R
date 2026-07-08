from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import importlib
import pkgutil
import sys


@dataclass
class CrossModuleValidationResult:
    scanned_modules: list[str] = field(default_factory=list)
    import_failures: list[str] = field(default_factory=list)
    success: bool = True


class CrossModuleValidator:
    def _sdk_root(self) -> Path:
        current = Path(__file__).resolve()
        for parent in current.parents:
            if parent.name == "AI5R-SDK":
                return parent
        raise RuntimeError("AI5R-SDK root not found")

    def scan_packages(self):
        sdk_root = self._sdk_root()

        if str(sdk_root) not in sys.path:
            sys.path.insert(0, str(sdk_root))

        return [
            m.name
            for m in pkgutil.iter_modules([str(sdk_root)])
            if not m.name.startswith("__")
        ]

    def validate_imports(self) -> CrossModuleValidationResult:
        result = CrossModuleValidationResult()

        modules = self.scan_packages()

        for module in modules:
            result.scanned_modules.append(module)

            try:
                importlib.import_module(module)
            except Exception:
                result.import_failures.append(module)
                result.success = False

        return result
