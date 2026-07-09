from SALES.CRM.customer import Customer
from SALES.CRM.interaction import CustomerInteraction


class SalesCRMRuntime:
    def __init__(self):
        self.customers: dict[str, Customer] = {}
        self.interactions: dict[str, list[CustomerInteraction]] = {}

    def add_customer(self, customer: Customer):
        if customer.customer_id in self.customers:
            raise ValueError("Duplicate customer")

        self.customers[customer.customer_id] = customer
        self.interactions[customer.customer_id] = []

    def get_customer(self, customer_id: str) -> Customer:
        if customer_id not in self.customers:
            raise KeyError("Customer not found")

        return self.customers[customer_id]

    def record_interaction(self, interaction: CustomerInteraction):
        if interaction.customer_id not in self.customers:
            raise KeyError("Customer not found")

        self.interactions[interaction.customer_id].append(interaction)

    def customer_history(self, customer_id: str) -> list[CustomerInteraction]:
        if customer_id not in self.customers:
            raise KeyError("Customer not found")

        return list(self.interactions[customer_id])

    def latest_interaction(self, customer_id: str) -> CustomerInteraction | None:
        history = self.customer_history(customer_id)

        if not history:
            return None

        return history[-1]

    def next_followup(self, customer_id: str) -> str | None:
        latest = self.latest_interaction(customer_id)

        if latest is None:
            return None

        return latest.next_followup_at

    def update_status(self, customer_id: str, status: str):
        customer = self.get_customer(customer_id)
        customer.status = status
        return customer
