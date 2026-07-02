import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REGISTRY_DIR = ROOT / "AI5R-SDK" / "FACTORY" / "REGISTRY" / "MODULES"
PRODUCT = "LTSA-BRAIN"

def valid_json(path):
    with open(path, "r", encoding="utf-8") as f:
        json.load(f)

def test_module(module):
    result = subprocess.run(
        ["python3", "AI5R-SDK/FACTORY/factory.py", module, PRODUCT],
        cwd=ROOT,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return False, result.stderr

    build_pack = ROOT / "PRODUCTS" / PRODUCT / "BUILD-PACKS" / f"BP-{module}"

    required_dirs = [
        build_pack / "DATABASE",
        build_pack / "WORKFLOWS",
        build_pack / "SCHEMAS",
    ]

    for d in required_dirs:
        if not d.exists():
            return False, f"Missing directory: {d}"

    workflows = list((build_pack / "WORKFLOWS").glob("*.json"))
    sql_files = list((build_pack / "DATABASE").glob("*.sql"))
    schema_files = list((build_pack / "SCHEMAS").glob("*.json"))

    if len(workflows) < 5:
        return False, f"Expected 5 workflows, found {len(workflows)}"

    if len(sql_files) < 1:
        return False, "No SQL files generated"

    if len(schema_files) < 2:
        return False, f"Expected schema + openapi, found {len(schema_files)}"

    for wf in workflows:
        valid_json(wf)

    for schema in schema_files:
        valid_json(schema)

    return True, "PASS"

def main():
    print("========================================")
    print("AI5R Factory Regression Suite")
    print("========================================")

    registries = sorted(REGISTRY_DIR.glob("*.json"))

    if not registries:
        raise SystemExit("No registry files found")

    passed = 0
    failed = 0

    for registry in registries:
        module = registry.stem.upper()
        ok, message = test_module(module)

        if ok:
            passed += 1
            print(f"{module:<20} PASS")
        else:
            failed += 1
            print(f"{module:<20} FAIL")
            print(f"  {message}")

    print("----------------------------------------")
    print(f"TOTAL  : {len(registries)}")
    print(f"PASSED : {passed}")
    print(f"FAILED : {failed}")
    print("========================================")

    if failed > 0:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
