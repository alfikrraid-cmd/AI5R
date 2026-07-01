#!/usr/bin/env python3

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
MODULE_SPEC_DIR = BASE_DIR / "MODULE-SPECS"


def load_module(module_name: str):
    spec_file = MODULE_SPEC_DIR / f"{module_name}.json"

    if not spec_file.exists():
        raise FileNotFoundError(f"Module Spec not found: {spec_file}")

    with open(spec_file, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    spec = load_module("pump")
    print(json.dumps(spec, indent=2))
