from __future__ import annotations

from dataclasses import dataclass, field
import importlib
import pkgutil


@dataclass
class CrossModuleValidationResult:
    scanned_modules: list[str] = field(default_factory=list)
    import_failures: list[str] = field(default_factory=list)
    success: bool = True

    def mark_failure(self, module: str):
        self.import_failures.append(module)
        self.success = False


class CrossModuleValidator:
    def __init__(self, root_package: str = "AI5R-SDK"):
        self.root_package = root_package

    def scan_packages(self):
        import AI5R_SDK  # alias safety import

        return [m.name for m in pkgutil.walk_packages(AI5R_SDK.__path__, AI5R_SDK.__name__ + ".")]

    def validate_imports(self) -> CrossModuleValidationResult:
        result = CrossModuleValidationResult()

        modules = self.scan_packages()

        for module in modules:
            result.scanned_modules.append(module)

            try:
                importlib.import_module(module)
            except Exception:
                result.mark_failure(module)

        return result
