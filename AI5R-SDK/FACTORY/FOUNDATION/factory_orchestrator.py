try:
    from .factory_validator import FactoryValidator
    from .factory_compiler import FactoryCompiler
    from .factory_freeze import FactoryFreeze
except ImportError:
    from factory_validator import FactoryValidator
    from factory_compiler import FactoryCompiler
    from factory_freeze import FactoryFreeze


class FactoryOrchestrator:
    """
    Orchestrates validation, compilation, and freeze for factory definitions.

    `context` is additive (UMR-001, MWO-LTSA-049) -- passed through to the
    compiler unchanged when supplied; omitting it preserves every
    pre-existing caller's behavior exactly.
    """

    def __init__(
        self,
        validator: FactoryValidator,
        compiler: FactoryCompiler,
        freezer: FactoryFreeze,
    ):
        self.validator = validator
        self.compiler = compiler
        self.freezer = freezer

    def manufacture(self, definition: dict, context=None) -> dict:
        validation = self.validator.validate(definition)

        if validation["status"] != "VALID":
            return {
                "status": "MANUFACTURING_REJECTED",
                "validation": validation,
            }

        compiled = self.compiler.compile(definition, context=context)

        frozen = self.freezer.freeze(
            product=definition["product"],
            version=definition["version"],
            result=compiled,
        )

        return {
            "status": "MANUFACTURING_COMPLETED",
            "validation": validation,
            "compiled": compiled,
            "frozen": frozen,
        }
