CANONICAL_FACTORY_MAP = {
    "manufacturing_order": {
        "canonical": "MANUFACTURING.ORDERS.manufacturing_order",
        "compatibility": [
            "FACTORY.ORDERS.manufacturing_order",
        ],
        "status": "CANONICAL_CONFIRMED",
        "rule": "All new code must use MANUFACTURING.ORDERS.ManufacturingOrder",
    },
    "manufacturing_engine": {
        "canonical": "MANUFACTURING.manufacturing_engine",
        "compatibility": [
            "FACTORY.MANUFACTURING.manufacturing_engine",
        ],
        "status": "NEEDS_CONFIRMATION",
    },
    "base_manufacturing_station": {
        "canonical": "FACTORY.CORE.manufacturing_station",
        "compatibility": [],
        "status": "ACTIVE",
    },
    "station_registry": {
        "canonical": "FACTORY.REGISTRY.station_registry",
        "compatibility": [
            "FACTORY.FOUNDATION.station_registry",
            "FACTORY.MANUFACTURING.station_registry",
            "STATION_REGISTRY",
        ],
        "status": "NEEDS_CONSOLIDATION",
    },
    "manufacturing_order_validator": {
        "canonical": "FACTORY.VALIDATION.manufacturing_order_validator",
        "compatibility": [],
        "status": "ACTIVE_BUT_REVIEW_AFTER_ORDER_CANONICAL",
    },
}


def get_canonical(component_name: str) -> str:
    if component_name not in CANONICAL_FACTORY_MAP:
        raise KeyError(f"Unknown factory component: {component_name}")

    return CANONICAL_FACTORY_MAP[component_name]["canonical"]


def get_status(component_name: str) -> str:
    if component_name not in CANONICAL_FACTORY_MAP:
        raise KeyError(f"Unknown factory component: {component_name}")

    return CANONICAL_FACTORY_MAP[component_name]["status"]


def list_components_needing_confirmation() -> list[str]:
    return [
        component
        for component, config in CANONICAL_FACTORY_MAP.items()
        if config["status"] in {"NEEDS_CONFIRMATION", "NEEDS_CONSOLIDATION"}
    ]
