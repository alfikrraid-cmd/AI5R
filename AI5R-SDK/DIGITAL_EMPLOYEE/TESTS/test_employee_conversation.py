from DIGITAL_EMPLOYEE.CONVERSATION import (
    EmployeeConversation,
    EmployeeConversationStore,
)


def test_create_conversation():
    conversation = EmployeeConversation(
        employee_id="EMP-001",
        title="Daily Work",
    )

    assert conversation.employee_id == "EMP-001"
    assert conversation.title == "Daily Work"
    assert conversation.conversation_id.startswith("CONV-")


def test_add_message():
    conversation = EmployeeConversation(
        employee_id="EMP-001",
    )

    conversation.add_message(
        role="user",
        content="Hello",
    )

    assert len(conversation.messages) == 1
    assert conversation.messages[0]["content"] == "Hello"


def test_store_create():
    store = EmployeeConversationStore()

    conversation = store.create(
        employee_id="EMP-001",
        title="Planning",
    )

    assert store.get(
        conversation.conversation_id
    ) is conversation


def test_store_list():
    store = EmployeeConversationStore()

    store.create("EMP-001")
    store.create("EMP-001")
    store.create("EMP-002")

    assert len(store.list("EMP-001")) == 2


def test_store_delete():
    store = EmployeeConversationStore()

    conversation = store.create("EMP-001")

    assert store.delete(
        conversation.conversation_id
    )

    assert store.count() == 0


def test_snapshot():
    conversation = EmployeeConversation(
        employee_id="EMP-001"
    )

    conversation.add_message(
        role="assistant",
        content="Done",
    )

    snapshot = conversation.snapshot()

    assert snapshot["employee_id"] == "EMP-001"
    assert len(snapshot["messages"]) == 1
