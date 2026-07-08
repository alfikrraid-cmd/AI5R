from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class EnterpriseObject:
    object_id: str
    object_type: str
    name: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )


class EnterpriseObjectType:

    ENTERPRISE = "enterprise"

    COMPANY = "company"

    BRANCH = "branch"

    BRAND = "brand"

    DEPARTMENT = "department"

    DIVISION = "division"

    PROJECT = "project"

    CUSTOMER = "customer"

    VENDOR = "vendor"

    EMPLOYEE = "employee"

    ASSET = "asset"

    INVENTORY = "inventory"

    BANK_ACCOUNT = "bank_account"

    PAYMENT_CHANNEL = "payment_channel"

    TAX_PROFILE = "tax_profile"

    COST_CENTER = "cost_center"

    PROFIT_CENTER = "profit_center"
