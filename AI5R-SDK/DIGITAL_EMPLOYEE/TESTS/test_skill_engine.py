from DIGITAL_EMPLOYEE.SKILLS import SkillEngine


def test_register_skill():
    engine = SkillEngine()

    skill = engine.register_skill(
        "EMP-001",
        "Python",
    )

    assert skill.skill_name == "Python"
    assert skill.level == 1


def test_gain_experience():
    engine = SkillEngine()

    skill = engine.register_skill(
        "EMP-001",
        "Python",
    )

    engine.gain_experience(
        skill.skill_id,
        50,
    )

    assert skill.experience_points == 50
    assert skill.level == 1


def test_level_up():
    engine = SkillEngine()

    skill = engine.register_skill(
        "EMP-001",
        "Python",
    )

    engine.gain_experience(
        skill.skill_id,
        100,
    )

    assert skill.level == 2
    assert skill.experience_points == 0


def test_list_skills():
    engine = SkillEngine()

    engine.register_skill("EMP-001", "Python")
    engine.register_skill("EMP-001", "SQL")
    engine.register_skill("EMP-002", "Excel")

    assert len(engine.list_skills("EMP-001")) == 2


def test_snapshot():
    engine = SkillEngine()

    skill = engine.register_skill(
        "EMP-001",
        "Python",
    )

    snapshot = engine.snapshot()

    assert skill.skill_id in snapshot
