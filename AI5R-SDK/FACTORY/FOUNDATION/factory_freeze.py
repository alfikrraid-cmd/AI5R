from datetime import datetime, UTC


class FactoryFreeze:
    """
    Creates immutable freeze records for factory manufacturing results.
    """

    def freeze(self, product: str, version: str, result: dict) -> dict:
        return {
            "status": "FROZEN",
            "product": product,
            "version": version,
            "frozen_at": datetime.now(UTC).isoformat(),
            "result": result,
        }
