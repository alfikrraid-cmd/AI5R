from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class Meeting:
    title: str
    participants: list[str]
    agenda: list[str]
    status: str = "SCHEDULED"
    notes: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    meeting_id: str = field(default_factory=lambda: f"MTG-{uuid4()}")
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class MeetingRuntime:

    def __init__(self):
        self._meetings = []

    def schedule(
        self,
        title: str,
        participants: list[str],
        agenda: list[str],
    ):
        meeting = Meeting(
            title=title,
            participants=participants,
            agenda=agenda,
        )

        self._meetings.append(meeting)

        return {
            "status": "SCHEDULED",
            "meeting": meeting,
        }

    def start(self, meeting_id: str):
        for meeting in self._meetings:
            if meeting.meeting_id == meeting_id:
                meeting.status = "IN_PROGRESS"
                return {
                    "status": "IN_PROGRESS",
                    "meeting": meeting,
                }

        return {
            "status": "NOT_FOUND",
            "meeting": None,
        }

    def add_note(self, meeting_id: str, note: str):
        for meeting in self._meetings:
            if meeting.meeting_id == meeting_id:
                meeting.notes.append(note)
                return {
                    "status": "NOTE_ADDED",
                    "meeting": meeting,
                }

        return {
            "status": "NOT_FOUND",
            "meeting": None,
        }

    def add_decision(self, meeting_id: str, decision: str):
        for meeting in self._meetings:
            if meeting.meeting_id == meeting_id:
                meeting.decisions.append(decision)
                return {
                    "status": "DECISION_ADDED",
                    "meeting": meeting,
                }

        return {
            "status": "NOT_FOUND",
            "meeting": None,
        }

    def complete(self, meeting_id: str):
        for meeting in self._meetings:
            if meeting.meeting_id == meeting_id:
                meeting.status = "COMPLETED"
                return {
                    "status": "COMPLETED",
                    "meeting": meeting,
                }

        return {
            "status": "NOT_FOUND",
            "meeting": None,
        }

    def list_all(self):
        return self._meetings
