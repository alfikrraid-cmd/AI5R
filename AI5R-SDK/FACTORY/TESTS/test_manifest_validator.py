import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from VALIDATORS.manifest_validator import ManifestValidator


def test_validator():

    manifest = {

        "product":"LTSA-BRAIN",

        "entities":[

            {

                "entity":"pump",

                "fields":[

                    {

                        "name":"pump_code",

                        "type":"string"

                    }

                ]

            }

        ]

    }

    validator = ManifestValidator()

    assert validator.validate_product(manifest) is True


if __name__ == "__main__":
    test_validator()
    print("FM-005.3 Validation Engine OK")
