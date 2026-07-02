"""
AI5R Digital Factory
FM-001.4
FM-002 Product Build Engine
"""

import sys

from MANUFACTURING.service import ManufacturingService
from MANUFACTURING.product_builder import ProductBuilder


def main():

    if len(sys.argv) not in (2, 3):
        print("Usage:")
        print("python3 factory.py <module> [product]")
        print("python3 factory.py build <product>")
        sys.exit(1)

    command = sys.argv[1]

    if command.lower() == "build":
        product = sys.argv[2] if len(sys.argv) == 3 else "LTSA-BRAIN"
        builder = ProductBuilder()
        success = builder.build(product)

        if not success:
            sys.exit(1)

        return

    module = command
    product = sys.argv[2] if len(sys.argv) == 3 else "LTSA-BRAIN"

    service = ManufacturingService()

    path = service.manufacture_module(module, product)

    print(f"Manufacturing completed: {path}")


if __name__ == "__main__":
    main()
