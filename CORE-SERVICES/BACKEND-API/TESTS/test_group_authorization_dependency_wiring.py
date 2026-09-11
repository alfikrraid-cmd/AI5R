"""
MWO-LTSA-069 -- regression guard for dependencies.py's own real (never
overridden) wiring of get_group_authorization_repository().

Every existing group-agent test (test_whatsapp_group_agent_router.py,
test_whatsapp_group_agent_admin_router.py) overrides this dependency with
InMemoryGroupAuthorizationRepository for speed/CI-runnability -- correct
for those tests' own purpose, but it means no test anywhere asserted what
dependencies.py actually wires when NOT overridden. A read-only production
audit (see ENGINEERING/MWO/MWO-LTSA-069-*.md) confirmed the real wiring is
already the persistent Postgres-backed repository, and that migration
032's effect is already live in production with real ACTIVE groups -- so
a silent revert back to the in-memory fallback would silently reset
authorization state on every process restart without anyone noticing
until groups mysteriously lost access. This test exists purely to catch
that regression; it performs no I/O (WhatsAppGroupAuthorizationRepository
connects lazily, per its own docstring, so constructing/inspecting it here
touches no network or database).
"""
from __future__ import annotations

from dependencies import get_group_authorization_repository

# Import order matters here: dependencies.py performs the sys.path insert
# that makes the bare `API` package importable (see its own top-of-file
# comment) -- these two imports must come after it, exactly like every
# existing test in this directory orders `import main` before `from
# API...` imports.
from API.whatsapp_group_repository_inmemory import InMemoryGroupAuthorizationRepository
from API.whatsapp_group_repository_postgres import WhatsAppGroupAuthorizationRepository


def test_group_authorization_repository_is_postgres_backed_by_default():
    repo = get_group_authorization_repository()
    assert isinstance(repo, WhatsAppGroupAuthorizationRepository)
    assert not isinstance(repo, InMemoryGroupAuthorizationRepository)


def test_group_authorization_repository_is_a_singleton():
    # dependencies.py constructs one module-level instance and returns it
    # from every call -- never a fresh instance per request. Re-creating a
    # new one per call would still be "Postgres-backed" but would defeat
    # the point of sharing one DatabaseRunner-backed object.
    assert get_group_authorization_repository() is get_group_authorization_repository()
