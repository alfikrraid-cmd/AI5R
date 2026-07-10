import sys

import pytest


class FakeOrganizationRuntime:
    def __init__(self, assign_result=None):
        self.assign_calls = []
        self._assign_result = assign_result

    def assign(self, work_order):
        self.assign_calls.append(work_order)
        return self._assign_result if self._assign_result is not None else work_order


def make_work_order(**overrides):
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    defaults = dict(
        work_order_id="WO-100",
        objective="Launch the customer analytics dashboard",
        priority="HIGH",
        constraints=["budget<=100000"],
        success_criteria=["adoption >= 30%"],
        requested_roles=["ROLE-DESIGN", "ROLE-DATA"],
    )
    defaults.update(overrides)
    return ExecutiveWorkOrder(**defaults)


def test_inherits_from_ai_executive():
    from ORGANIZATION.ai_executive import AIExecutive
    from ORGANIZATION.product_manager import ProductManager

    pm = ProductManager()

    assert isinstance(pm, AIExecutive)


def test_constructor_supports_no_arguments():
    from ORGANIZATION.product_manager import ProductManager

    pm = ProductManager()

    assert pm.organization_runtime is None
    assert pm.executive_id
    assert pm.executive_name
    assert pm.department
    assert pm.authority_level


def test_constructor_stores_injected_runtime():
    from ORGANIZATION.product_manager import ProductManager

    runtime = FakeOrganizationRuntime()
    pm = ProductManager(organization_runtime=runtime)

    assert pm.organization_runtime is runtime


def test_receive_work_returns_the_same_work_order():
    from ORGANIZATION.product_manager import ProductManager

    pm = ProductManager()
    work_order = make_work_order()

    received = pm.receive_work(work_order)

    assert received is work_order


def test_receive_work_rejects_invalid_work_order():
    from ORGANIZATION.product_manager import ProductManager

    pm = ProductManager()

    with pytest.raises(ValueError):
        pm.receive_work({"work_order_id": "WO-100"})


def test_plan_is_deterministic():
    from ORGANIZATION.product_manager import ProductManager

    pm = ProductManager()
    work_order = make_work_order()

    first = pm.plan(work_order)
    second = pm.plan(work_order)

    assert first == second
    assert first == {
        "product_name": "WO-100",
        "objective": "Launch the customer analytics dashboard",
        "features": ["ROLE-DESIGN", "ROLE-DATA"],
        "constraints": ["budget<=100000"],
        "priority": "HIGH",
    }


def test_plan_uses_metadata_product_name_when_present():
    from ORGANIZATION.product_manager import ProductManager

    pm = ProductManager()
    work_order = make_work_order(metadata={"product_name": "Analytics Dashboard"})

    plan = pm.plan(work_order)

    assert plan["product_name"] == "Analytics Dashboard"


def test_plan_rejects_invalid_work_order():
    from ORGANIZATION.product_manager import ProductManager

    pm = ProductManager()

    with pytest.raises(ValueError):
        pm.plan(None)


def test_assign_delegates_to_injected_runtime():
    from ORGANIZATION.product_manager import ProductManager

    runtime = FakeOrganizationRuntime(assign_result="ASSIGNED")
    pm = ProductManager(organization_runtime=runtime)
    work_order = make_work_order()

    result = pm.assign(work_order)

    assert result == "ASSIGNED"
    assert runtime.assign_calls == [work_order]


def test_assign_without_runtime_raises():
    from ORGANIZATION.product_manager import ProductManager

    pm = ProductManager()
    work_order = make_work_order()

    with pytest.raises(ValueError):
        pm.assign(work_order)


def test_assign_rejects_invalid_work_order():
    from ORGANIZATION.product_manager import ProductManager

    runtime = FakeOrganizationRuntime()
    pm = ProductManager(organization_runtime=runtime)

    with pytest.raises(ValueError):
        pm.assign({"work_order_id": "WO-100"})


def test_monitor_returns_deterministic_snapshot():
    from ORGANIZATION.product_manager import ProductManager

    pm = ProductManager()

    first = pm.monitor()
    second = pm.monitor()

    assert first == second
    assert first["executive_id"] == pm.executive_id
    assert first["department"] == pm.department


def test_report_returns_deterministic_report():
    from ORGANIZATION.product_manager import ProductManager

    pm = ProductManager()

    first = pm.report({"status": "SUCCESS"})
    second = pm.report({"status": "SUCCESS"})

    assert first == second
    assert first["executive_id"] == pm.executive_id
    assert first["result"] == {"status": "SUCCESS"}


def test_stateless_across_runs():
    from ORGANIZATION.product_manager import ProductManager

    pm = ProductManager()
    work_order = make_work_order()

    pm.plan(work_order)
    pm.monitor()
    pm.report({"status": "SUCCESS"})

    assert pm.metadata == {}
    assert pm.plan(work_order) == pm.plan(work_order)


def test_stateless_between_independent_instances():
    from ORGANIZATION.product_manager import ProductManager

    first = ProductManager(organization_runtime=FakeOrganizationRuntime())
    second = ProductManager()

    first.monitor()

    assert second.organization_runtime is None


def test_product_manager_is_independent_of_manufacturing_center():
    for module_name in list(sys.modules):
        if module_name.startswith("MANUFACTURING_CENTER"):
            del sys.modules[module_name]

    import ORGANIZATION.product_manager  # noqa: F401

    assert not any(
        module_name.startswith("MANUFACTURING_CENTER")
        for module_name in sys.modules
    )
