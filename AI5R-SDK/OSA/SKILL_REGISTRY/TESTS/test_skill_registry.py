import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.SKILL_REGISTRY import SkillDefinition, SkillRegistry


def test_skill_registry_registers_skill():
    registry = SkillRegistry()

    skill = registry.register(
        SkillDefinition(
            skill_id="SKILL-CONTENT-001",
            name="Campaign Planner",
            capability="ContentPlanning",
            description="Creates campaign plans",
        )
    )

    assert skill.skill_id == "SKILL-CONTENT-001"
    assert registry.get("SKILL-CONTENT-001") == skill


def test_skill_registry_lists_skills():
    registry = SkillRegistry()

    registry.register(
        SkillDefinition(
            skill_id="SKILL-MARKET-001",
            name="Market Researcher",
            capability="MarketAnalysis",
        )
    )

    registry.register(
        SkillDefinition(
            skill_id="SKILL-FINANCE-001",
            name="Financial Planner",
            capability="FinancialPlanning",
        )
    )

    assert len(registry.list_skills()) == 2


def test_skill_registry_finds_by_capability():
    registry = SkillRegistry()

    registry.register(
        SkillDefinition(
            skill_id="SKILL-CONTENT-001",
            name="Campaign Planner",
            capability="ContentPlanning",
        )
    )

    registry.register(
        SkillDefinition(
            skill_id="SKILL-CONTENT-002",
            name="Content Calendar Builder",
            capability="ContentPlanning",
        )
    )

    matches = registry.find_by_capability("ContentPlanning")

    assert len(matches) == 2
    assert matches[0].capability == "ContentPlanning"


def test_skill_registry_resolves_best_skill():
    registry = SkillRegistry()

    registry.register(
        SkillDefinition(
            skill_id="SKILL-GENERAL-001",
            name="General Reasoner",
            capability="GeneralReasoning",
        )
    )

    skill = registry.resolve_best_skill("GeneralReasoning")

    assert skill.skill_id == "SKILL-GENERAL-001"


def test_skill_registry_requires_skill_id_and_capability():
    registry = SkillRegistry()

    try:
        registry.register(
            SkillDefinition(
                skill_id="",
                name="Broken Skill",
                capability="GeneralReasoning",
            )
        )
    except ValueError as error:
        assert str(error) == "skill_id is required"
    else:
        raise AssertionError("ValueError was not raised")

    try:
        registry.register(
            SkillDefinition(
                skill_id="SKILL-BROKEN",
                name="Broken Skill",
                capability="",
            )
        )
    except ValueError as error:
        assert str(error) == "capability is required"
    else:
        raise AssertionError("ValueError was not raised")


def test_skill_registry_raises_when_skill_missing():
    registry = SkillRegistry()

    try:
        registry.get("SKILL-MISSING")
    except KeyError as error:
        assert str(error) == "'Skill not found: SKILL-MISSING'"
    else:
        raise AssertionError("KeyError was not raised")


def test_skill_registry_raises_when_capability_has_no_skill():
    registry = SkillRegistry()

    try:
        registry.resolve_best_skill("UnknownCapability")
    except KeyError as error:
        assert str(error) == "'No skill registered for capability: UnknownCapability'"
    else:
        raise AssertionError("KeyError was not raised")
