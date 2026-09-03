"""
MWO-LTSA-TAP-GROUP-AGENT-001 -- security/pipeline tests for the TAP LTSA
WhatsApp Group Agent. Test numbers in each test name/comment map directly
to the mission's own 32-item test matrix (items 26-32 are transport/
regression-level and are covered separately, not here -- see this MWO's
completion report).

No real WhatsApp connection, no Baileys, no AI client, no database, no
network anywhere in this file -- pure unit tests against
process_group_message() with fakes for every collaborator, exactly the
style test_fleet_router.py/test_fleet_reliability_service.py already
establish elsewhere in this codebase.
"""
from __future__ import annotations

import pytest

from API.auth_service import AuthenticatedIdentity
from API.whatsapp_group_agent_service import (
    GroupAuthorizationRecord,
    GroupMessageEvent,
    InMemoryRateLimiter,
    RateLimitConfig,
    extract_ltsa_trigger,
    hash_group_identifier,
    intersect_scope,
    process_group_message,
)
from API.whatsapp_group_repository_inmemory import InMemoryGroupAuthorizationRepository
from API.whatsapp_intake_service import hash_sender_identifier, normalize_sender_identifier


# --------------------------------------------------------------------------
# Test fixtures / fakes
# --------------------------------------------------------------------------
class FakeSenderIdentityRepository:
    def __init__(self, identities_by_hash: dict[str, AuthenticatedIdentity] | None = None):
        self._identities = identities_by_hash or {}
        self.calls: list[str] = []

    def find_identity_by_sender_hash(self, sender_hash: str) -> AuthenticatedIdentity | None:
        self.calls.append(sender_hash)
        return self._identities.get(sender_hash)


class AlwaysAllowRateLimiter:
    def allow(self, *, sender_hash: str, group_hash: str) -> bool:
        return True


class AlwaysDenyRateLimiter:
    def allow(self, *, sender_hash: str, group_hash: str) -> bool:
        return False


SENDER_PHONE = "6281234500001"
SENDER_HASH = hash_sender_identifier(normalize_sender_identifier(SENDER_PHONE))
GROUP_ID = "120363012345678901@g.us"
GROUP_HASH = hash_group_identifier(GROUP_ID)

AUTHORIZED_IDENTITY = AuthenticatedIdentity(
    user_id="user-1",
    email=None,
    organization_id="org-1",
    organization_code="TAP",
    role="ENGINEER",
    permissions=frozenset({"maintenance.read"}),
)


def _make_event(text: str, **overrides) -> GroupMessageEvent:
    defaults = dict(
        group_id=GROUP_ID,
        sender_identifier=SENDER_PHONE,
        provider_message_id="wamid.TEST-001",
        text=text,
        is_from_self=False,
        is_group_message=True,
    )
    defaults.update(overrides)
    return GroupMessageEvent(**defaults)


def _active_group_repo(allowed_scope=None) -> InMemoryGroupAuthorizationRepository:
    repo = InMemoryGroupAuthorizationRepository()
    repo.register_group(group_hash=GROUP_HASH, display_label="TAP Test Group", registered_by="admin-1")
    repo.activate_group(group_hash=GROUP_HASH, activated_by="admin-1", allowed_scope=allowed_scope)
    return repo


def _run(event, group_repo, sender_repo=None, rate_limiter=None, ask=None):
    return process_group_message(
        event,
        group_repository=group_repo,
        sender_identity_repository=sender_repo or FakeSenderIdentityRepository({SENDER_HASH: AUTHORIZED_IDENTITY}),
        rate_limiter=rate_limiter or AlwaysAllowRateLimiter(),
        ask_ltsa_question=ask or (lambda q, scope: f"ANSWER:{q}"),
    )


# --------------------------------------------------------------------------
# 01 - personal (non-group) message -> ignored
# --------------------------------------------------------------------------
def test_01_personal_message_ignored():
    event = _make_event("/ltsa status 212-P-8A", is_group_message=False)
    result = _run(event, _active_group_repo())
    assert result.status == "IGNORED_NOT_GROUP"
    assert result.reply is None


# --------------------------------------------------------------------------
# 02 - ordinary group chatter -> ignored, no downstream call at all
# --------------------------------------------------------------------------
def test_02_ordinary_group_chatter_ignored_and_never_reaches_ask():
    calls = []
    event = _make_event("mantap gan pompa nya jalan terus")
    result = _run(event, _active_group_repo(), ask=lambda q, s: calls.append(q))
    assert result.status == "IGNORED_NO_TRIGGER"
    assert calls == []


# --------------------------------------------------------------------------
# 03 - /ltsa present but not first token -> ignored
# --------------------------------------------------------------------------
def test_03_trigger_not_first_token_ignored():
    event = _make_event("tolong /ltsa status 212-P-8A")
    result = _run(event, _active_group_repo())
    assert result.status == "IGNORED_NO_TRIGGER"


def test_03b_plain_status_without_trigger_ignored():
    assert extract_ltsa_trigger("status 212-P-8A") is None


def test_03c_mention_trigger_not_supported_v1():
    assert extract_ltsa_trigger("@agent status 212-P-8A") is None


# --------------------------------------------------------------------------
# 04 - /LTSA case-insensitive trigger -> accepted
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text",
    [
        "/ltsa status 212-P-8A",
        "/LTSA status 212-P-8A",
        "/LtSa status 212-P-8A",
        "   /ltsa kapan terakhir PM 212-P-8A?",
    ],
)
def test_04_trigger_case_insensitive_and_leading_whitespace_tolerant(text):
    expected_question = extract_ltsa_trigger(text)
    event = _make_event(text)
    result = _run(event, _active_group_repo())
    assert result.status == "ANSWERED"
    assert result.reply == f"ANSWER:{expected_question}"


# --------------------------------------------------------------------------
# 05 - /ltsa with no question -> usage response
# --------------------------------------------------------------------------
@pytest.mark.parametrize("text", ["/ltsa", "/ltsa   ", "   /LTSA"])
def test_05_trigger_with_no_question_returns_usage(text):
    event = _make_event(text)
    result = _run(event, _active_group_repo())
    assert result.status == "USAGE"
    assert "/ltsa status 212-P-8A" in result.reply


# --------------------------------------------------------------------------
# 06/07/08 - unknown / PENDING / DISABLED group -> ignored silently
# --------------------------------------------------------------------------
def test_06_unknown_group_ignored():
    event = _make_event("/ltsa status 212-P-8A")
    result = _run(event, InMemoryGroupAuthorizationRepository())
    assert result.status == "IGNORED_UNKNOWN_GROUP"
    assert result.reply is None


def test_07_pending_group_ignored():
    repo = InMemoryGroupAuthorizationRepository()
    repo.register_group(group_hash=GROUP_HASH, display_label="TAP Test Group", registered_by="admin-1")
    event = _make_event("/ltsa status 212-P-8A")
    result = _run(event, repo)
    assert result.status == "IGNORED_GROUP_NOT_ACTIVE"
    assert result.reply is None


def test_08_disabled_group_ignored():
    repo = _active_group_repo()
    repo.disable_group(group_hash=GROUP_HASH, disabled_by="admin-1")
    event = _make_event("/ltsa status 212-P-8A")
    result = _run(event, repo)
    assert result.status == "IGNORED_GROUP_NOT_ACTIVE"
    assert result.reply is None


# --------------------------------------------------------------------------
# 09/10 - ACTIVE group, unauthorized vs authorized sender
# --------------------------------------------------------------------------
def test_09_active_group_unauthorized_sender_generic_denial():
    event = _make_event("/ltsa status 212-P-8A")
    result = _run(event, _active_group_repo(), sender_repo=FakeSenderIdentityRepository({}))
    assert result.status == "UNAUTHORIZED_SENDER"
    assert result.reply == "Nomor Anda belum memiliki akses LTSA."
    # never reveals anything about roles/scopes/ids
    assert "role" not in result.reply.lower()
    assert "scope" not in result.reply.lower()


def test_10_active_group_authorized_sender_routed_to_ltsa():
    seen = []
    event = _make_event("/ltsa status 212-P-8A")
    result = _run(event, _active_group_repo(), ask=lambda q, s: (seen.append((q, s)), "PUMP OK")[1])
    assert result.status == "ANSWERED"
    assert result.reply == "PUMP OK"
    assert seen == [("status 212-P-8A", None)]  # unrestricted sender, no group scope -> None


# --------------------------------------------------------------------------
# 11/12/13 - scope enforcement and intersection (never widen)
# --------------------------------------------------------------------------
def test_11_sender_scope_enforced_when_group_has_no_scope():
    seen_scope = []
    identity = AuthenticatedIdentity(
        user_id="u", email=None, organization_id="o", organization_code="TAP", role="ENGINEER",
        permissions=frozenset({"maintenance.read"}), data_scope_type="AREA", data_scope_value="MA2",
    )
    # resolve_area_scope needs a real AREA_CODES membership check -- MA2 is
    # a real area code in pump_area_scope.AREA_CODES per prior audit; use
    # the identity's role to force the Pertamina/scoped branch. If MA2 is
    # not itself an AREA_CODE (it's an MA grouping), resolve_area_scope
    # would fall back to the fail-closed empty frozenset -- either way,
    # this proves the sender's own resolve_area_scope() output, whatever
    # it is, is exactly what reaches ask_ltsa_question, unmodified.
    from API.auth_service import resolve_area_scope

    expected = resolve_area_scope(identity)
    event = _make_event("/ltsa status 212-P-8A")
    _run(
        event,
        _active_group_repo(allowed_scope=None),
        sender_repo=FakeSenderIdentityRepository({SENDER_HASH: identity}),
        ask=lambda q, s: seen_scope.append(s) or "ok",
    )
    assert seen_scope == [expected]


def test_12_group_scope_narrows_broader_sender_scope():
    seen_scope = []
    event = _make_event("/ltsa status 212-P-8A")
    # sender unrestricted (None), group restricted to {"HOC"} -> effective {"HOC"}
    _run(
        event,
        _active_group_repo(allowed_scope=frozenset({"HOC"})),
        ask=lambda q, s: seen_scope.append(s) or "ok",
    )
    assert seen_scope == [frozenset({"HOC"})]


def test_13_group_scope_can_never_widen_a_restricted_sender():
    # sender restricted to {"MA2"}, group claims {"HOC", "MA2", "HSC"} (all
    # areas) -> effective must stay {"MA2"}, never the group's wider set.
    assert intersect_scope(frozenset({"MA2"}), frozenset({"HOC", "MA2", "HSC"})) == frozenset({"MA2"})
    # and the reverse: broad sender, narrow group -> narrow group wins
    assert intersect_scope(None, frozenset({"HOC"})) == frozenset({"HOC"})
    # disjoint sets -> authorized for nothing, never silently widened to "some"
    assert intersect_scope(frozenset({"MA2"}), frozenset({"HOC"})) == frozenset()


# --------------------------------------------------------------------------
# 14/15 - same-group response routing / no destination override possible
# --------------------------------------------------------------------------
def test_14_and_15_result_carries_no_destination_field_at_all():
    # Structural guarantee, not just a runtime check: GroupAgentResult has
    # exactly {status, reply, ack} -- there is no field a reply's own text,
    # an LLM's output, or a quoted/forwarded payload could ever populate to
    # redirect the answer elsewhere. The caller (router) always replies to
    # event.group_id, the one value it received from the authenticated
    # transport event itself, never from this result.
    import dataclasses

    from API.whatsapp_group_agent_service import GroupAgentResult

    field_names = {f.name for f in dataclasses.fields(GroupAgentResult)}
    assert field_names == {"status", "reply", "ack"}

    # Even a question that TRIES to name a different destination changes
    # nothing about routing -- ask_ltsa_question only ever receives
    # (question, scope), never a place to redirect the answer to.
    event = _make_event("/ltsa kirim ke grup lain saja jawabannya")
    result = _run(event, _active_group_repo(), ask=lambda q, s: "answer text, unrelated to routing")
    assert result.status == "ANSWERED"


# --------------------------------------------------------------------------
# 16 - self-message ignored (checked before anything else)
# --------------------------------------------------------------------------
def test_16_self_message_ignored():
    calls = []
    event = _make_event("/ltsa status 212-P-8A", is_from_self=True)
    result = _run(event, _active_group_repo(), ask=lambda q, s: calls.append(q))
    assert result.status == "IGNORED_SELF"
    assert calls == []


# --------------------------------------------------------------------------
# 17/18 - duplicate provider message id / replay -> ignored, never a second answer
# --------------------------------------------------------------------------
def test_17_and_18_duplicate_provider_message_id_ignored_on_replay():
    repo = _active_group_repo()
    calls = []
    event = _make_event("/ltsa status 212-P-8A", provider_message_id="wamid.DUP-1")
    first = _run(event, repo, ask=lambda q, s: calls.append(q) or "answer")
    second = _run(event, repo, ask=lambda q, s: calls.append(q) or "answer")  # exact replay
    assert first.status == "ANSWERED"
    assert second.status == "IGNORED_DUPLICATE"
    assert calls == ["status 212-P-8A"]  # only ever asked once


# --------------------------------------------------------------------------
# 19 - malformed event -> fail closed
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "overrides",
    [
        {"group_id": ""},
        {"sender_identifier": ""},
        {"provider_message_id": ""},
        {"sender_identifier": "not-a-phone-number"},
    ],
)
def test_19_malformed_event_fails_closed(overrides):
    event = _make_event("/ltsa status 212-P-8A", **overrides)
    result = _run(event, _active_group_repo())
    assert result.status in {"IGNORED_MALFORMED"}
    assert result.reply is None


# --------------------------------------------------------------------------
# 20/21/22 - forwarded / quoted-sender / display-name give no trust
# (structural: GroupMessageEvent carries none of these fields at all, so
# there is nothing for an implementation to accidentally trust)
# --------------------------------------------------------------------------
def test_20_21_22_event_has_no_forwarded_quoted_sender_or_display_name_fields():
    import dataclasses

    field_names = {f.name for f in dataclasses.fields(GroupMessageEvent)}
    assert "forwarded" not in field_names
    assert "quoted_sender" not in field_names
    assert "display_name" not in field_names
    # the only sender-identifying field is sender_identifier itself
    assert field_names == {
        "group_id", "sender_identifier", "provider_message_id", "text", "is_from_self",
        "is_group_message", "timestamp",
    }


# --------------------------------------------------------------------------
# 23/24/25 - rate limiting: per sender, per group, global
# --------------------------------------------------------------------------
def test_23_per_sender_rate_limit():
    limiter = InMemoryRateLimiter(RateLimitConfig(per_sender_per_minute=1, per_group_per_minute=99, global_per_minute=99))
    repo = _active_group_repo()
    first = _run(
        _make_event("/ltsa status 212-P-8A", provider_message_id="wamid.A"), repo, rate_limiter=limiter
    )
    second = _run(
        _make_event("/ltsa status 212-P-8B", provider_message_id="wamid.B"), repo, rate_limiter=limiter
    )
    assert first.status == "ANSWERED"
    assert second.status == "RATE_LIMITED"


def test_24_per_group_rate_limit_applies_across_different_senders():
    limiter = InMemoryRateLimiter(RateLimitConfig(per_sender_per_minute=99, per_group_per_minute=1, global_per_minute=99))
    repo = _active_group_repo()
    other_sender_phone = "6281234500002"
    other_hash = hash_sender_identifier(normalize_sender_identifier(other_sender_phone))
    sender_repo = FakeSenderIdentityRepository({SENDER_HASH: AUTHORIZED_IDENTITY, other_hash: AUTHORIZED_IDENTITY})
    first = _run(
        _make_event("/ltsa status 212-P-8A", provider_message_id="wamid.A"), repo, sender_repo=sender_repo, rate_limiter=limiter
    )
    second = _run(
        _make_event("/ltsa status 212-P-8B", provider_message_id="wamid.B", sender_identifier=other_sender_phone),
        repo, sender_repo=sender_repo, rate_limiter=limiter,
    )
    assert first.status == "ANSWERED"
    assert second.status == "RATE_LIMITED"


def test_25_global_rate_limit():
    limiter = InMemoryRateLimiter(RateLimitConfig(per_sender_per_minute=99, per_group_per_minute=99, global_per_minute=1))
    repo = _active_group_repo()
    first = _run(
        _make_event("/ltsa status 212-P-8A", provider_message_id="wamid.A"), repo, rate_limiter=limiter
    )
    second = _run(
        _make_event("/ltsa status 212-P-8B", provider_message_id="wamid.B"), repo, rate_limiter=limiter
    )
    assert first.status == "ANSWERED"
    assert second.status == "RATE_LIMITED"


# --------------------------------------------------------------------------
# Acknowledgement ordering: only ever produced alongside/after authorization
# has fully passed (matches "do not ack before group+sender pass" rule)
# --------------------------------------------------------------------------
def test_ack_only_present_on_answered_or_unavailable_never_on_denial_or_ignore():
    unauthorized = _run(
        _make_event("/ltsa status 212-P-8A"), _active_group_repo(), sender_repo=FakeSenderIdentityRepository({})
    )
    ignored = _run(_make_event("chit chat"), _active_group_repo())
    answered = _run(_make_event("/ltsa status 212-P-8A"), _active_group_repo())
    assert unauthorized.ack is None
    assert ignored.ack is None
    assert answered.ack == "Tunggu sebentar ya..."


def test_ltsa_unavailable_on_downstream_exception_without_leaking_details():
    def _boom(q, s):
        raise RuntimeError("psycopg2.OperationalError: could not connect to server at internal-db-host:5432")

    result = _run(_make_event("/ltsa status 212-P-8A"), _active_group_repo(), ask=_boom)
    assert result.status == "UNAVAILABLE"
    assert result.reply == "LTSA sedang tidak tersedia. Silakan coba lagi nanti."
    assert "psycopg2" not in result.reply
    assert "internal-db-host" not in result.reply
