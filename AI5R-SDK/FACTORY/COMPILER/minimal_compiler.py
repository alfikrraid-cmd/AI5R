"""
FM-004.6 Minimal Compiler

Transforms a Product Manifest into EntityIR.
Compiler is the only producer of IR.
"""

from IR.entity_ir import EntityIR


class MinimalCompiler:
    def compile_entity(self, manifest: dict) -> EntityIR:
        entity = manifest.get("entity") or manifest.get("name")

        if not entity:
            raise ValueError("Product manifest must contain 'entity' or 'name'")

        fields = manifest.get("fields", [])

        if not isinstance(fields, list):
            raise ValueError("'fields' must be a list")

        return EntityIR(
            name=entity,
            fields=fields
        )
