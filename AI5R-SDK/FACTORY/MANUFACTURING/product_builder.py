from pathlib import Path

from MANUFACTURING.service import ManufacturingService


class ProductBuilder:

    def __init__(self):
        self.registry = Path("AI5R-SDK/FACTORY/REGISTRY/MODULES")
        self.service = ManufacturingService()

    def build(self, product):

        modules = sorted(self.registry.glob("*.json"))

        passed = 0
        failed = 0

        print("=" * 40)
        print("AI5R PRODUCT BUILD")
        print("=" * 40)
        print()

        for module in modules:

            name = module.stem.upper()

            try:
                self.service.manufacture_module(name, product)

                print(f"{name:<20} PASS")

                passed += 1

            except Exception as e:

                print(f"{name:<20} FAIL")

                print(e)

                failed += 1

        print("-" * 40)
        print(f"TOTAL : {len(modules)}")
        print(f"PASS  : {passed}")
        print(f"FAIL  : {failed}")
        print("=" * 40)

        return failed == 0
