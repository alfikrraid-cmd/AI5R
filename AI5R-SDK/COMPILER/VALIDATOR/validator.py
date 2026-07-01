"""
AI5R Compiler Validator
BC-23
"""

import json
from pathlib import Path


REQUIRED_KEYS = [
    "module",
    "resource",
    "operation",
    "endpoint",
    "database"
]


class ValidationError(Exception):
    pass


def load_spec(path):
    with open(path, "r") as f:
        return json.load(f)


def validate_required(spec):
    missing = []

    for key in REQUIRED_KEYS:
        if key not in spec:
            missing.append(key)

    if missing:
        raise ValidationError(
            "Missing required keys: " + ", ".join(missing)
        )


def validate(spec_path):
    spec = load_spec(spec_path)

    validate_required(spec)

    print("Module Spec Validation PASSED")


if __name__ == "__main__":
    import sys

    validate(sys.argv[1])
