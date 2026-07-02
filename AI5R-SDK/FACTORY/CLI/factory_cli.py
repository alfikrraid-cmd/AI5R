#!/usr/bin/env python3
"""
AI5R Digital Factory CLI
FM-003 Factory CLI
"""

import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FACTORY = ROOT / "AI5R-SDK" / "FACTORY"
PRODUCTS = ROOT / "PRODUCTS"


def run_cmd(cmd):
    result = subprocess.run(cmd, cwd=ROOT)
    return result.returncode


def cmd_version():
    print("AI5R Digital Factory CLI")
    print("Version: FM-003")
    print("Core: FM-001 Production Release")
    print("Product Build Engine: FM-002")
    return 0


def cmd_list():
    print("Available products:")
    if PRODUCTS.exists():
        for p in sorted(PRODUCTS.iterdir()):
            if p.is_dir():
                print(f"- {p.name}")
    return 0


def cmd_build(args):
    if len(args) != 1:
        print("Usage: factory build <PRODUCT>")
        return 1

    product = args[0]
    return run_cmd([
        "python3",
        str(FACTORY / "factory.py"),
        "build",
        product
    ])


def cmd_test():
    return run_cmd([
        "python3",
        str(FACTORY / "TESTS" / "regression.py")
    ])


def cmd_doctor():
    checks = [
        FACTORY / "factory.py",
        FACTORY / "MANUFACTURING" / "service.py",
        FACTORY / "TESTS" / "regression.py",
        PRODUCTS,
    ]

    ok = True
    for path in checks:
        if path.exists():
            print(f"OK   {path.relative_to(ROOT)}")
        else:
            print(f"MISS {path.relative_to(ROOT)}")
            ok = False

    return 0 if ok else 1


def cmd_release(args):
    if len(args) != 1:
        print("Usage: factory release <PRODUCT>")
        return 1

    product = args[0]
    print(f"Running release verification for {product}...")
    test_code = cmd_test()
    if test_code != 0:
        print("Release failed: regression test failed")
        return test_code

    print(f"Release verification passed for {product}")
    return 0


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  factory version")
        print("  factory list")
        print("  factory build <PRODUCT>")
        print("  factory test")
        print("  factory doctor")
        print("  factory release <PRODUCT>")
        return 1

    command = sys.argv[1]
    args = sys.argv[2:]

    if command == "version":
        return cmd_version()
    if command == "list":
        return cmd_list()
    if command == "build":
        return cmd_build(args)
    if command == "test":
        return cmd_test()
    if command == "doctor":
        return cmd_doctor()
    if command == "release":
        return cmd_release(args)

    print(f"Unknown command: {command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
