from __future__ import annotations

from dataclasses import dataclass, field
import importlib
import pkgutil
import AI5R_SDK


@dataclass
class CrossModuleValidationResult:
    scanned_modules: list[str] = field(default_factory=list)
    import_failures: list[str] = field(default_factory=list)
    success: bool = True


class CrossModuleValidator:
    def scan_packages(self):
        return [
            m.name
            for m in pkgutil.walk_packages(
                AI5R_SDK.__path__,
                AI5R_SDK.__name__ + "."
            )
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
