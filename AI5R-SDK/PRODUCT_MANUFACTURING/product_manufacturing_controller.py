from PRODUCT_ENGINE import ProductSpecification
from PRODUCT_RUNTIME import ProductRuntime


class ProductManufacturingController:
    def __init__(self, root_path):
        self.root_path = root_path
        self.runtime = ProductRuntime(root_path)

    def manufacture(self, specification: ProductSpecification):
        runtime_context = self.runtime.start(specification)

        return {
            "status": "PRODUCT_RUNNING",
            "product": runtime_context["product"],
            "version": runtime_context["version"],
            "runtime_status": runtime_context["status"],
            "domains": runtime_context["domains"],
            "artifact_path": runtime_context["artifact_path"],
            "started_at": runtime_context["started_at"],
        }

    def stop(self, product_name: str):
        stopped = self.runtime.stop(product_name)

        if stopped is None:
            return {
                "status": "NOT_FOUND",
                "product": product_name,
            }

        return {
            "status": "PRODUCT_STOPPED",
            "product": stopped["product"],
            "runtime_status": stopped["status"],
            "stopped_at": stopped["stopped_at"],
        }

    def status(self, product_name: str):
        runtime_status = self.runtime.status(product_name)

        if runtime_status is None:
            return {
                "status": "NOT_FOUND",
                "product": product_name,
            }

        return {
            "status": "PRODUCT_STATUS",
            "product": runtime_status["product"],
            "runtime_status": runtime_status["status"],
            "domains": runtime_status["domains"],
        }
