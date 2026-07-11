import pytest

from ORGANIZATION.executive_work_order import ExecutiveWorkOrder


class FakeCTO:
    def __init__(self, plan_result=None):
        self.receive_work_calls = []
        self.plan_calls = []
        self._plan_result = plan_result if plan_result is not None else {"cto": "plan"}

    def receive_work(self, work_order):
        self.receive_work_calls.append(work_order)
        return work_order

    def plan(self, work_order):
        self.plan_calls.append(work_order)
        return self._plan_result


class FakeProductManager:
    def __init__(self, plan_result=None):
        self.plan_calls = []
        self._plan_result = (
            plan_result if plan_result is not None else {"product_manager": "plan"}
        )

    def plan(self, work_order):
        self.plan_calls.append(work_order)
        return self._plan_result


class FakeSolutionArchitect:
    def __init__(self, plan_result=None):
        self.plan_calls = []
        self._plan_result = plan_result if plan_result is not None else {
            "architecture_name": "WO-200",
            "product_name": "Payments Platform",
            "modules": ["ROLE-BACKEND"],
            "services": [],
            "apis": [],
            "database": [],
            "constraints": [],
            "priority": "HIGH",
        }

    def plan(self, work_order):
        self.plan_calls.append(work_order)
        return dict(self._plan_result)


class FakeProductionLine:
    def __init__(self, artifacts=None):
        self.produce_calls = []
        self._artifacts = artifacts if artifacts is not None else {"index.html": "<html></html>"}

    def produce(self, technical_architecture):
        self.produce_calls.append(technical_architecture)
        return dict(self._artifacts)


class FakeBundleBuilder:
    def __init__(self, bundle_result=None):
        self.bundle_calls = []
        self._bundle_result = bundle_result if bundle_result is not None else {
            "manifest.json": {"product_name": "Payments Platform"},
            "website": {},
            "api": {},
            "docs": {},
            "tests": {},
        }

    def bundle(self, product_name, artifacts):
        self.bundle_calls.append((product_name, artifacts))
        return dict(self._bundle_result)


def make_work_order(**overrides):
    defaults = dict(
        work_order_id="WO-200",
        objective="Build a payments platform",
        priority="HIGH",
        constraints=["budget<=200000"],
        success_criteria=["launch<=90d"],
        requested_roles=["ROLE-BACKEND", "ROLE-DATABASE"],
        metadata={"product_name": "Payments Platform"},
    )
    defaults.update(overrides)
    return ExecutiveWorkOrder(**defaults)


_UNSET = object()


def make_demo(
    cto=_UNSET,
    product_manager=_UNSET,
    solution_architect=_UNSET,
    production_line=_UNSET,
    bundle_builder=_UNSET,
):
    from DEMO.end_to_end_manufacturing_demo import EndToEndManufacturingDemo

    return EndToEndManufacturingDemo(
        cto=FakeCTO() if cto is _UNSET else cto,
        product_manager=FakeProductManager() if product_manager is _UNSET else product_manager,
        solution_architect=(
            FakeSolutionArchitect() if solution_architect is _UNSET else solution_architect
        ),
        production_line=(
            FakeProductionLine() if production_line is _UNSET else production_line
        ),
        bundle_builder=(
            FakeBundleBuilder() if bundle_builder is _UNSET else bundle_builder
        ),
    )


def test_manufacture_rejects_invalid_work_order():
    demo = make_demo()

    with pytest.raises(ValueError):
        demo.manufacture({"work_order_id": "WO-200"})


def test_manufacture_raises_when_cto_missing():
    demo = make_demo(cto=None)
    work_order = make_work_order()

    with pytest.raises(ValueError):
        demo.manufacture(work_order)


def test_manufacture_raises_when_product_manager_missing():
    demo = make_demo(product_manager=None)
    work_order = make_work_order()

    with pytest.raises(ValueError):
        demo.manufacture(work_order)


def test_manufacture_raises_when_solution_architect_missing():
    demo = make_demo(solution_architect=None)
    work_order = make_work_order()

    with pytest.raises(ValueError):
        demo.manufacture(work_order)


def test_manufacture_raises_when_production_line_missing():
    demo = make_demo(production_line=None)
    work_order = make_work_order()

    with pytest.raises(ValueError):
        demo.manufacture(work_order)


def test_manufacture_raises_when_bundle_builder_missing():
    demo = make_demo(bundle_builder=None)
    work_order = make_work_order()

    with pytest.raises(ValueError):
        demo.manufacture(work_order)


def test_manufacture_runs_successful_pipeline_in_order():
    cto = FakeCTO()
    product_manager = FakeProductManager()
    solution_architect = FakeSolutionArchitect()
    production_line = FakeProductionLine(artifacts={"index.html": "<html></html>"})
    bundle_builder = FakeBundleBuilder()
    demo = make_demo(
        cto=cto,
        product_manager=product_manager,
        solution_architect=solution_architect,
        production_line=production_line,
        bundle_builder=bundle_builder,
    )
    work_order = make_work_order()

    result = demo.manufacture(work_order)

    assert cto.receive_work_calls == [work_order]
    assert cto.plan_calls == [work_order]
    assert product_manager.plan_calls == [work_order]
    assert solution_architect.plan_calls == [work_order]
    assert production_line.produce_calls == [solution_architect._plan_result]
    assert bundle_builder.bundle_calls == [
        ("Payments Platform", {"index.html": "<html></html>"})
    ]
    assert result == bundle_builder._bundle_result


def test_manufacture_is_deterministic():
    demo = make_demo()
    work_order = make_work_order()

    first = demo.manufacture(work_order)
    second = demo.manufacture(work_order)

    assert first == second


def test_manufacture_is_stateless_across_runs():
    demo = make_demo()
    work_order = make_work_order()

    demo.manufacture(work_order)
    demo.manufacture(work_order)
    demo.manufacture(work_order)

    assert demo.manufacture(work_order) == demo.manufacture(work_order)


def test_manufacture_uses_injected_dependencies():
    bundle_builder_a = FakeBundleBuilder(bundle_result={"manifest.json": {}, "website": {}, "api": {}, "docs": {}, "tests": {}, "marker": "A"})
    bundle_builder_b = FakeBundleBuilder(bundle_result={"manifest.json": {}, "website": {}, "api": {}, "docs": {}, "tests": {}, "marker": "B"})
    demo_a = make_demo(bundle_builder=bundle_builder_a)
    demo_b = make_demo(bundle_builder=bundle_builder_b)
    work_order = make_work_order()

    assert demo_a.manufacture(work_order)["marker"] == "A"
    assert demo_b.manufacture(work_order)["marker"] == "B"


def test_manufacture_returns_bundled_product_with_expected_sections():
    demo = make_demo()
    work_order = make_work_order()

    result = demo.manufacture(work_order)

    assert set(["manifest.json", "website", "api", "docs", "tests"]).issubset(result.keys())
