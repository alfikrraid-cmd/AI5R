from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_EMPLOYEE import GoalEngine
from DIGITAL_EMPLOYEE import SkillEngine
from DIGITAL_EMPLOYEE import PerformanceEngine
from DIGITAL_EMPLOYEE import EmployeeInbox
from DIGITAL_EMPLOYEE import EmployeeMemoryStore
from DIGITAL_EMPLOYEE import EmployeeConversationStore

from OS import MultiAgentRuntime
from INTEGRATION import SystemIntegrationRunner


def test_beta_integration():
    runtime = MultiAgentRuntime()

    runner = SystemIntegrationRunner()

    steps = [
        ("agent", lambda: runtime.start_agent("EMP-001")),
        ("goal", lambda: GoalEngine().create_goal("EMP-001", "Sales")),
        ("skill", lambda: SkillEngine().register_skill("EMP-001", "Negotiation")),
        ("inbox", lambda: EmployeeInbox().send_message("EMP-001", "EMP-002", "A", "B")),
        ("memory", lambda: EmployeeMemoryStore().store("EMP-001", "T", {"x": 1})),
        ("conversation", lambda: EmployeeConversationStore().create("EMP-001")),
        ("performance", lambda: PerformanceEngine().record_success("EMP-001")),
    ]

    report = runner.run(steps)

    assert report.success is True
    assert len(report.executed_steps) == len(steps)
