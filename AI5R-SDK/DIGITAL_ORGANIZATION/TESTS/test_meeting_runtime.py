import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_ORGANIZATION import MeetingRuntime


def test_meeting_runtime():

    runtime = MeetingRuntime()

    result = runtime.schedule(
        title="Launch Planning",
        participants=[
            "CEO",
            "Marketing Manager",
            "Finance Manager",
        ],
        agenda=[
            "Campaign strategy",
            "Budget review",
        ],
    )

    meeting = result["meeting"]

    assert result["status"] == "SCHEDULED"
    assert meeting.title == "Launch Planning"
    assert meeting.status == "SCHEDULED"
    assert meeting.meeting_id.startswith("MTG-")
    assert len(meeting.participants) == 3

    started = runtime.start(meeting.meeting_id)
    assert started["status"] == "IN_PROGRESS"

    note = runtime.add_note(
        meeting.meeting_id,
        "Marketing proposed a 14-day campaign.",
    )
    assert note["status"] == "NOTE_ADDED"
    assert len(note["meeting"].notes) == 1

    decision = runtime.add_decision(
        meeting.meeting_id,
        "Approve campaign with budget limit.",
    )
    assert decision["status"] == "DECISION_ADDED"
    assert len(decision["meeting"].decisions) == 1

    completed = runtime.complete(meeting.meeting_id)
    assert completed["status"] == "COMPLETED"
    assert completed["meeting"].status == "COMPLETED"

    assert runtime.list_all() == [meeting]
