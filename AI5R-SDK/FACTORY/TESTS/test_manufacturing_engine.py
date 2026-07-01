import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

PRODUCT = "LTSA-BRAIN"
MODULE = "PUMP"

BUILD_PACK = ROOT / "PRODUCTS" / PRODUCT / "BUILD-PACKS" / "BP-PUMP"

EXPECTED_FILES = [
    BUILD_PACK / "README.md",
    BUILD_PACK / "SCHEMAS" / "pump.schema.json",
    BUILD_PACK / "SCHEMAS" / "pump.openapi.json",
]

def assert_file_exists(path):
    if not path.exists():
        raise AssertionError(f"Missing file: {path}")

def assert_valid_json(path):
    with open(path, "r") as f:
        json.load(f)

def main():
    print("FM-001.9 Manufacturing Engine Test Started")

    result = subprocess.run(
        ["python3", "AI5R-SDK/FACTORY/factory.py", MODULE, PRODUCT],
        cwd=ROOT,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise SystemExit("Factory execution failed")

    for file_path in EXPECTED_FILES:
        assert_file_exists(file_path)

    workflows = sorted((BUILD_PACK / "WORKFLOWS").glob("*.json"))
    sql_files = sorted(BUILD_PACK.rglob("*.sql"))

    if len(workflows) < 5:
        raise AssertionError(f"Expected at least 5 workflow JSON files, found {len(workflows)}")

    if len(sql_files) < 1:
        raise AssertionError("Expected at least 1 SQL migration file, found 0")

    assert_valid_json(BUILD_PACK / "SCHEMAS" / "pump.schema.json")
    assert_valid_json(BUILD_PACK / "SCHEMAS" / "pump.openapi.json")

    for wf in workflows:
        assert_valid_json(wf)

    print("Generated workflow files:")
    for wf in workflows:
        print(f"- {wf.name}")

    print("Generated SQL files:")
    for sql in sql_files:
        print(f"- {sql.relative_to(BUILD_PACK)}")

    print("FM-001.9 Manufacturing Engine Test PASSED")

if __name__ == "__main__":
    main()
