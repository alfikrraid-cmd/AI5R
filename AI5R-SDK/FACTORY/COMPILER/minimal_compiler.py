"""
FM-004.6 Minimal Compiler

Transforms a Product Manifest into EntityIR.
Compiler is the only producer of IR.
"""

from IR.entity_ir import EntityIR
from IR.compilation_unit import CompilationUnit


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

    def compile_product(self, manifest: dict) -> CompilationUnit:
        product = manifest.get("product") or manifest.get("name")

        if not product:
            raise ValueError("Product manifest must contain 'product' or 'name'")

        entities = manifest.get("entities", [])

        if not isinstance(entities, list):
            raise ValueError("'entities' must be a list")

        unit = CompilationUnit(
            product=product,
            metadata=manifest.get("metadata", {})
        )

        for entity_manifest in entities:
            unit.add_entity(self.compile_entity(entity_manifest))

        return unit

