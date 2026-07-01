#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
COMPILER_DIR = BASE_DIR / "COMPILER"


def build(module_name: str, workflow_type: str):
    cmd = [
        "python3",
        str(COMPILER_DIR / "workflow_generator.py"),
        module_name,
        workflow_type,
    ]

    print("=" * 50)
    print("AI5R SDK Compiler")
    print("=" * 50)
    print(f"Module   : {module_name}")
    print(f"Workflow : {workflow_type}")
    print()

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print()
        print("✓ Build SUCCESS")
    else:
        print()
        print("✗ Build FAILED")
        sys.exit(result.returncode)


def main():
    if len(sys.argv) != 4:
        print("Usage:")
        print("python3 ai5r.py build <module> <workflow>")
        sys.exit(1)

    command = sys.argv[1]

    if command != "build":
        print(f"Unknown command: {command}")
        sys.exit(1)

    build(sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    main()
