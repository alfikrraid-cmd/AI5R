from DIGITAL_EMPLOYEE.INBOX import (
    EmployeeInbox,
    EmployeeMessage,
    EmployeeMessagePriority,
    EmployeeMessageStatus,
)


def test_employee_message_creation():
    message = EmployeeMessage(
        sender_id="EMP-001",
        recipient_id="EMP-002",
        subject="Task",
        body="Please review this task.",
        priority=EmployeeMessagePriority.HIGH,
    )

    assert message.message_id.startswith("MSG-")
    assert message.sender_id == "EMP-001"
    assert message.recipient_id == "EMP-002"
    assert message.subject == "Task"
    assert message.body == "Please review this task."
    assert message.priority == EmployeeMessagePriority.HIGH
    assert message.status == EmployeeMessageStatus.NEW
    assert message.created_at


def test_employee_message_rejects_missing_sender():
    try:
        EmployeeMessage(
            sender_id="",
            recipient_id="EMP-002",
            subject="Task",
            body="Body",
        )
    except ValueError as exc:
        assert "Sender ID is required" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_employee_message_rejects_missing_recipient():
    try:
        EmployeeMessage(
            sender_id="EMP-001",
            recipient_id="",
            subject="Task",
            body="Body",
        )
    except ValueError as exc:
        assert "Recipient ID is required" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_employee_message_mark_read():
    message = EmployeeMessage(
        sender_id="EMP-001",
        recipient_id="EMP-002",
        subject="Task",
        body="Body",
    )

    message.mark_read()

    assert message.status == EmployeeMessageStatus.READ
    assert message.read_at is not None


def test_employee_message_archive():
    message = EmployeeMessage(
        sender_id="EMP-001",
        recipient_id="EMP-002",
        subject="Task",
        body="Body",
    )

    message.archive()

    assert message.status == EmployeeMessageStatus.ARCHIVED
    assert message.archived_at is not None


def test_employee_inbox_send_and_get_message():
    inbox = EmployeeInbox()

    message = inbox.send_message(
        sender_id="EMP-001",
        recipient_id="EMP-002",
        subject="Task",
        body="Please execute.",
        priority="URGENT",
        metadata={"workflow_id": "WF-001"},
    )

    loaded = inbox.get_message(message.message_id)

    assert loaded is message
    assert loaded.priority == EmployeeMessagePriority.URGENT
    assert loaded.metadata["workflow_id"] == "WF-001"


def test_employee_inbox_list_messages_by_recipient():
    inbox = EmployeeInbox()

    inbox.send_message("EMP-001", "EMP-002", "A", "Body A")
    inbox.send_message("EMP-003", "EMP-002", "B", "Body B")
    inbox.send_message("EMP-001", "EMP-004", "C", "Body C")

    messages = inbox.list_messages("EMP-002")

    assert len(messages) == 2
    assert {message.subject for message in messages} == {"A", "B"}


def test_employee_inbox_unread_count():
    inbox = EmployeeInbox()

    first = inbox.send_message("EMP-001", "EMP-002", "A", "Body A")
    inbox.send_message("EMP-003", "EMP-002", "B", "Body B")

    inbox.mark_read(first.message_id)

    assert inbox.unread_count("EMP-002") == 1


def test_employee_inbox_archive_hides_message_by_default():
    inbox = EmployeeInbox()

    first = inbox.send_message("EMP-001", "EMP-002", "A", "Body A")
    inbox.send_message("EMP-003", "EMP-002", "B", "Body B")

    inbox.archive(first.message_id)

    active_messages = inbox.list_messages("EMP-002")
    all_messages = inbox.list_messages("EMP-002", include_archived=True)

    assert len(active_messages) == 1
    assert len(all_messages) == 2
    assert active_messages[0].subject == "B"


def test_employee_inbox_requires_existing_message():
    inbox = EmployeeInbox()

    try:
        inbox.require_message("MSG-MISSING")
    except KeyError as exc:
        assert "Employee message not found" in str(exc)
    else:
        raise AssertionError("Expected KeyError")


def test_employee_inbox_snapshot_for_recipient():
    inbox = EmployeeInbox()

    inbox.send_message("EMP-001", "EMP-002", "Task", "Body")

    snapshot = inbox.snapshot("EMP-002")

    assert snapshot["recipient_id"] == "EMP-002"
    assert snapshot["unread_count"] == 1
    assert snapshot["messages"][0]["subject"] == "Task"
