from pathlib import Path

from .foundation_manifest import FoundationManifest


class FoundationGenerator:
    """
    AI5R Foundation Generator

    Generates canonical folder structure for a foundation.
    """

    def generate(self, manifest: FoundationManifest, root: str = "AI5R-SDK"):
        foundation_name = manifest.normalized_name()
        module_prefix = manifest.module_prefix()

        base = Path(root) / foundation_name
        tests = base / "TESTS"
        docs = base / "DOCS"

        base.mkdir(parents=True, exist_ok=True)

        if manifest.tests:
            tests.mkdir(parents=True, exist_ok=True)

        if manifest.docs:
            docs.mkdir(parents=True, exist_ok=True)

        files = []

        init_file = base / "__init__.py"
        init_file.write_text("")
        files.append(str(init_file))

        component_files = {
            "object": base / f"{module_prefix}_object.py",
            "registry": base / f"{module_prefix}_registry.py",
            "validation": base / f"{module_prefix}_validation_engine.py",
            "runtime": base / f"{module_prefix}_runtime.py",
            "manifest": base / f"{module_prefix}_manifest.py",
            "station": base / f"{module_prefix}_manufacturing_station.py",
        }

        for component, path in component_files.items():
            if component in manifest.components:
                path.write_text(
                    f'"""Generated {foundation_name} {component} component."""\n'
                )
                files.append(str(path))

                if manifest.tests:
                    test_path = tests / f"test_{module_prefix}_{component}.py"
                    test_path.write_text(
                        f"def test_{module_prefix}_{component}():\n"
                        f"    assert True\n"
                    )
                    files.append(str(test_path))

        if manifest.docs and "specification" in manifest.components:
            spec_path = docs / f"{manifest.code}-SPECIFICATION.md"
            spec_path.write_text(
                f"# {foundation_name} Foundation Specification\n\n"
                f"Version: {manifest.version}\n"
            )
            files.append(str(spec_path))

        if manifest.docs and "freeze" in manifest.components:
            freeze_path = docs / f"{foundation_name}-FOUNDATION-FREEZE-v{manifest.version}.md"
            freeze_path.write_text(
                f"# {foundation_name} Foundation Freeze v{manifest.version}\n\n"
                "Status:\nFROZEN\n"
            )
            files.append(str(freeze_path))

        return {
            "status": "GENERATED",
            "foundation": foundation_name,
            "files": files,
        }
