"""
AI5R Digital Factory
FM-001 Lite
"""

from pathlib import Path
import sys

ARTIFACTS = [
    "DATABASE",
    "WORKFLOWS",
    "SCHEMAS",
    "TESTS",
    "REPORTS"
]


def create_build_pack(module_name: str, product_name: str = "LTSA-BRAIN"):

    root = (
        Path("PRODUCTS")
        / product_name
        / "BUILD-PACKS"
        / f"BP-{module_name.upper()}"
    )

    root.mkdir(parents=True, exist_ok=True)

    for folder in ARTIFACTS:
        (root / folder).mkdir(exist_ok=True)

    readme = root / "README.md"
    readme.write_text(
        f"# Build Pack\n\nProduct: {product_name}\nModule: {module_name}\n",
        encoding="utf-8"
    )

    print(f"Build Pack created: {root}")


if __name__ == "__main__":

    if len(sys.argv) not in [2, 3]:
        print("Usage:")
        print("python3 factory.py <module> [product]")
        sys.exit(1)

    module = sys.argv[1]
    product = sys.argv[2] if len(sys.argv) == 3 else "LTSA-BRAIN"

    create_build_pack(module, product)
