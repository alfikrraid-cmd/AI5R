from PRODUCT_RUNTIME import ProductRuntime
from BUSINESS_VERTICALS.REGISTRY import VerticalRegistry


class AI5R:
    def __init__(self, root_path="."):
        self.product_runtime = ProductRuntime(root_path)
        self.active_product = None
        self.active_vertical = None
        self.vertical_registry = VerticalRegistry()

    def load(self, product_name: str, domains: list[str] | None = None):
        result = self.product_runtime.load(
            product_name=product_name,
            domains=domains,
        )
        self.active_product = result["product"]
        return result




    def use_vertical(self, vertical_name: str):
        runtime = self.vertical_registry.create(
            vertical_name,
            root_path=self.product_runtime.root_path,
        )

        try:
            started = runtime.start()
        except TypeError:
            started = runtime.start(
                {
                    "product": vertical_name,
                    "agents": [],
                }
            )

        self.active_vertical = runtime
        self.active_product = vertical_name

        return started

    def use(self, product_name: str, domains: list[str] | None = None):
        return self.load(
            product_name=product_name,
            domains=domains,
        )

    def ask(self, prompt: str, employee_id: str = "EMP-001"):
        return self.run(
            goal=prompt,
            employee_id=employee_id,
        )

    def run(self, goal: str, employee_id: str = "EMP-001"):
        if self.active_vertical:
            return self.active_vertical.run_goal(
                goal=goal,
                employee_id=employee_id,
            )

        if not self.active_product:
            raise ValueError("no active product loaded")

        return self.product_runtime.run_goal(
            product_name=self.active_product,
            goal=goal,
            employee_id=employee_id,
        )

    def status(self, product_name: str | None = None):
        target = product_name or self.active_product

        if not target:
            raise ValueError("no active product loaded")

        return self.product_runtime.status(target)

    def stop(self, product_name: str | None = None):
        target = product_name or self.active_product

        if not target:
            raise ValueError("no active product loaded")

        result = self.product_runtime.stop(target)

        if product_name is None:
            self.active_product = None
            self.active_vertical = None

        return result

    def list_products(self):
        return self.product_runtime.registry.list_all()

