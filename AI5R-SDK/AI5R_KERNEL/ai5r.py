from PRODUCT_RUNTIME import ProductRuntime


class AI5R:
    def __init__(self, root_path="."):
        self.product_runtime = ProductRuntime(root_path)
        self.active_product = None

    def load(self, product_name: str, domains: list[str] | None = None):
        result = self.product_runtime.load(
            product_name=product_name,
            domains=domains,
        )
        self.active_product = result["product"]
        return result

    def run(self, goal: str, employee_id: str = "EMP-001"):
        if not self.active_product:
            raise ValueError("no active product loaded")

        return self.product_runtime.run_goal(
            product_name=self.active_product,
            goal=goal,
            employee_id=employee_id,
        )
