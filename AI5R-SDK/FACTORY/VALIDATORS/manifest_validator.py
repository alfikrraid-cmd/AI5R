"""
FM-005.3
Manifest Validator
"""

class ManifestValidator:

    def validate_product(self, manifest):

        if "product" not in manifest:
            raise ValueError("Missing product")

        entities = manifest.get("entities")

        if not isinstance(entities, list):
            raise ValueError("'entities' must be a list")

        for entity in entities:

            if "entity" not in entity:
                raise ValueError("Entity missing name")

            fields = entity.get("fields")

            if not isinstance(fields, list):
                raise ValueError(
                    f"Entity '{entity['entity']}' fields must be list"
                )

            if len(fields) == 0:
                raise ValueError(
                    f"Entity '{entity['entity']}' has no fields"
                )

        return True
