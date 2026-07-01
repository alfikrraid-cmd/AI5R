"""
AI5R Digital Factory
FM-001.4
"""

import sys

from MANUFACTURING.service import ManufacturingService


def main():

    if len(sys.argv) not in (2, 3):
        print("Usage:")
        print("python3 factory.py <module> [product]")
        sys.exit(1)

    module = sys.argv[1]
    product = sys.argv[2] if len(sys.argv) == 3 else "LTSA-BRAIN"

    service = ManufacturingService()

    path = service.manufacture_module(module, product)

    print(f"Manufacturing completed: {path}")


if __name__ == "__main__":
    main()
