"""Contract tests for F1.2c — Browser Session Grant.

Each test maps to one acceptance criterion from the workpacket.
All tests are offline/deterministic — no network, no credentials.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from aptdata.auth import (
    BrowserSession,
    BrowserSessionGrantStore,
    GrantExpiredError,
    GrantNotFoundError,
    GrantRevokedError,
    GrantRunError,
    GrantScopeError,
    GrantWorkspaceError,
)
from aptdata.delivery.session_response import (
    BrowserSessionResponse,
    SessionCookie,
    SessionHeader,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store(tmp_path: Path) -> BrowserSessionGrantStore:
    """A BrowserSessionGrantStore backed by a temporary SQLite database."""
    return BrowserSessionGrantStore(db_path=str(tmp_path / "grants_test.db"))


SCOPES = ("capture:read", "run:view")


@pytest.fixture()
def grant(store: BrowserSessionGrantStore) -> str:
    """Issue a valid grant, return the raw token."""
    return store.issue(
        workspace_id="ws-main",
        project_id="proj-alpha",
        run_id="run-42",
        scopes=SCOPES,
    )


# ===========================================================================
# Acceptance criteria
# ===========================================================================


class TestIssue:
    """Criterion 1 & 2: issue returns opaque grant; store has no raw value."""

    def test_issue_returns_nonempty_string(self, store: BrowserSessionGrantStore):
        """Criterion 1: issue returns opaque non-empty grant."""
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=("read",),
        )
        assert raw
        assert isinstance(raw, str)
        assert len(raw) > 16
        assert re.fullmatch(r"[0-9a-f]+", raw)

    def test_store_has_no_raw_grant(self, store: BrowserSessionGrantStore):
        """Criterion 2: raw grant is not stored anywhere in the database."""
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=("read",),
        )
        # Verify via the dedicated test helper that scans every text column
        assert not store._raw_grant_in_store(raw)

        # Also verify the hash is stored (but not the raw)
        assert store._grant_count() == 1

    def test_two_grants_different_raw_values(self, store: BrowserSessionGrantStore):
        """Two successive issues produce different raw grants."""
        raw1 = store.issue(
            workspace_id="ws-a", project_id="p1", run_id="r1", scopes=("s1",)
        )
        raw2 = store.issue(
            workspace_id="ws-b", project_id="p2", run_id="r2", scopes=("s2",)
        )
        assert raw1 != raw2


class TestRedeem:
    """Criterion 3 & 4: valid redeem yields session; repeat fails."""

    def test_valid_redeem_returns_session(
        self, store: BrowserSessionGrantStore, grant: str,
    ):
        """Criterion 3: redeem returns a BrowserSession with correct metadata."""
        session = store.redeem(grant, workspace_id="ws-main", required_scopes=SCOPES)
        assert isinstance(session, BrowserSession)
        assert session.workspace_id == "ws-main"
        assert session.project_id == "proj-alpha"
        assert session.run_id == "run-42"
        assert session.scopes == SCOPES
        assert session.session_id
        assert len(session.session_id) > 16
        assert session.created_at.tzinfo is not None
        assert session.expires_at.tzinfo is not None
        assert session.expires_at > session.created_at

    def test_redeem_atomic_consumes_grant(
        self, store: BrowserSessionGrantStore, grant: str,
    ):
        """After redeem the grant row is gone (one grant -> zero grants)."""
        assert store._grant_count() == 1
        store.redeem(grant, workspace_id="ws-main")
        assert store._grant_count() == 0
        assert store._session_count() == 1

    def test_redeem_twice_fails(self, store: BrowserSessionGrantStore, grant: str):
        """Criterion 4: second redeem with same grant raises GrantNotFoundError."""
        store.redeem(grant, workspace_id="ws-main")
        with pytest.raises(GrantNotFoundError):
            store.redeem(grant, workspace_id="ws-main")


class TestExpiry:
    """Criterion 5: expired grant fails."""

    def test_expired_grant_fails(self, tmp_path: Path):
        """A grant issued with 0-second TTL expires immediately."""
        store = BrowserSessionGrantStore(
            db_path=str(tmp_path / "ttl_test.db"),
            ttl_seconds=0,
        )
        raw = store.issue(
            workspace_id="ws-x",
            project_id="p",
            run_id="r",
            scopes=("s",),
        )
        # With TTL=0, expires_at == created_at, so now_ts > expires_at
        with pytest.raises(GrantExpiredError):
            store.redeem(raw, workspace_id="ws-x")


class TestWorkspaceMismatch:
    """Criterion 6: workspace mismatch fails."""

    def test_wrong_workspace_fails(
        self, store: BrowserSessionGrantStore, grant: str,
    ):
        """Redeeming with a different workspace_id raises GrantWorkspaceError."""
        with pytest.raises(GrantWorkspaceError):
            store.redeem(grant, workspace_id="ws-other")

    def test_workspace_error_does_not_consume_grant(
        self, store: BrowserSessionGrantStore, grant: str,
    ):
        """A workspace-mismatch error leaves the grant intact."""
        with pytest.raises(GrantWorkspaceError):
            store.redeem(grant, workspace_id="ws-other")
        # Grant should still be usable with the correct workspace
        session = store.redeem(grant, workspace_id="ws-main")
        assert session.workspace_id == "ws-main"


class TestRunMismatch:
    """Criterion 7: run mismatch fails."""

    def test_run_mismatch_fails(
        self, store: BrowserSessionGrantStore, grant: str,
    ):
        """Redeeming with wrong run_id raises GrantRunError."""
        with pytest.raises(GrantRunError):
            store.redeem(grant, workspace_id="ws-main", run_id="run-other")

    def test_run_mismatch_does_not_consume(
        self, store: BrowserSessionGrantStore, grant: str,
    ):
        """Run mismatch leaves the grant intact for correct run."""
        with pytest.raises(GrantRunError):
            store.redeem(grant, workspace_id="ws-main", run_id="run-other")
        session = store.redeem(grant, workspace_id="ws-main", run_id="run-42")
        assert session.run_id == "run-42"


class TestScopeVerification:
    """Criterion 8: missing scope fails."""

    def test_missing_scope_fails(
        self, store: BrowserSessionGrantStore, grant: str,
    ):
        """Asking for a scope not in the grant raises GrantScopeError."""
        with pytest.raises(GrantScopeError):
            store.redeem(
                grant,
                workspace_id="ws-main",
                required_scopes=("capture:read", "admin"),
            )

    def test_subset_scopes_ok(
        self, store: BrowserSessionGrantStore, grant: str,
    ):
        """Asking for a subset of granted scopes is fine."""
        session = store.redeem(
            grant,
            workspace_id="ws-main",
            required_scopes=("capture:read",),
        )
        assert "capture:read" in session.scopes

    def test_empty_required_scopes_ok(
        self, store: BrowserSessionGrantStore, grant: str,
    ):
        """An empty required_scopes tuple is always satisfied."""
        session = store.redeem(grant, workspace_id="ws-main")
        assert session.scopes == SCOPES


class TestRevoke:
    """Criterion 9: revoke prevents redeem."""

    def test_revoke_prevents_redeem(
        self, store: BrowserSessionGrantStore, grant: str,
    ):
        """After revoke, redeem on that grant raises GrantRevokedError."""
        assert store.revoke(grant) is True
        with pytest.raises(GrantRevokedError):
            store.redeem(grant, workspace_id="ws-main")

    def test_revoke_twice_returns_false(
        self, store: BrowserSessionGrantStore, grant: str,
    ):
        """Revoking an already-revoked grant returns False."""
        store.revoke(grant)
        assert store.revoke(grant) is False

    def test_revoke_nonexistent_grant_returns_false(
        self, store: BrowserSessionGrantStore,
    ):
        """Revoking a grant that was never issued returns False."""
        assert store.revoke("nonexistent_grant_that_does_not_exist") is False


class TestSessionExpiry:
    """Criterion 10: session expiry (sessions also have a TTL)."""

    def test_session_has_expiry(
        self, store: BrowserSessionGrantStore, grant: str,
    ):
        """A redeemed session has a future expires_at."""
        session = store.redeem(grant, workspace_id="ws-main")
        assert session.expires_at > datetime.now(timezone.utc)


class TestRevokeSession:
    """Criterion 11: revoke_session works."""

    def test_revoke_session_after_redeem(
        self, store: BrowserSessionGrantStore, grant: str,
    ):
        """revoke_session marks a redeemed session as revoked."""
        session = store.redeem(grant, workspace_id="ws-main")
        assert store.revoke_session(session.session_id) is True

    def test_revoke_session_twice_returns_false(
        self, store: BrowserSessionGrantStore, grant: str,
    ):
        """Revoking an already-revoked session returns False."""
        session = store.redeem(grant, workspace_id="ws-main")
        store.revoke_session(session.session_id)
        assert store.revoke_session(session.session_id) is False

    def test_revoke_session_nonexistent_returns_false(
        self, store: BrowserSessionGrantStore,
    ):
        """Revoking a never-issued session returns False."""
        assert store.revoke_session("no-such-session") is False


class TestSanitization:
    """Criterion 12: no raw grant in repr, errors, or logs."""

    def test_repr_never_leaks_grant(
        self, store: BrowserSessionGrantStore, grant: str,
    ):
        """repr() of the session does not contain the raw grant."""
        session = store.redeem(grant, workspace_id="ws-main")
        r = repr(session)
        assert grant not in r
        assert session.session_id in r  # session_id is safe

    def test_exception_messages_no_grant(
        self, store: BrowserSessionGrantStore, grant: str,
    ):
        """Exception messages never contain the raw grant value."""
        # GrantWorkspaceError
        try:
            store.redeem(grant, workspace_id="ws-other")
        except GrantWorkspaceError as e:
            msg = str(e)
            assert grant not in msg
            assert "ws-main" in msg  # safe metadata is ok

        # GrantRunError
        try:
            store.redeem(grant, workspace_id="ws-main", run_id="run-other")
        except GrantRunError as e:
            msg = str(e)
            assert grant not in msg

    def test_hash_is_not_raw_grant(
        self, store: BrowserSessionGrantStore, grant: str,
    ):
        """The stored hash does not equal or contain the raw grant."""
        for row in store._conn.execute(
            "SELECT grant_hash FROM browser_session_grants"
        ).fetchall():
            assert row["grant_hash"] != grant
            assert grant not in row["grant_hash"]


class TestGrantIndependence:
    """Criterion 13: two grants for the same run are independent."""

    def test_two_grants_same_run_independent(
        self, store: BrowserSessionGrantStore,
    ):
        """Two grants for same run can be redeemed independently."""
        raw1 = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=("capture:read",),
        )
        raw2 = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=("capture:read",),
        )

        s1 = store.redeem(raw1, workspace_id="ws-main")
        s2 = store.redeem(raw2, workspace_id="ws-main")

        assert s1.session_id != s2.session_id
        assert s1.created_at <= s2.created_at


class TestPersistence:
    """Criterion 14: SQLite persistence survives close/reopen."""

    def test_grants_survive_reopen(self, tmp_path: Path):
        """Unredeemed grants are still available after close/reopen."""
        db = tmp_path / "persist.db"
        s1 = BrowserSessionGrantStore(db_path=str(db), ttl_seconds=3600)
        raw = s1.issue(
            workspace_id="ws-main",
            project_id="p",
            run_id="r",
            scopes=("s",),
        )
        s1.close()

        s2 = BrowserSessionGrantStore(db_path=str(db), ttl_seconds=3600)
        session = s2.redeem(raw, workspace_id="ws-main")
        assert session.workspace_id == "ws-main"
        s2.close()

    def test_sessions_survive_reopen(self, tmp_path: Path):
        """Redeemed sessions survive close/reopen."""
        db = tmp_path / "sessions_persist.db"
        s1 = BrowserSessionGrantStore(db_path=str(db), ttl_seconds=3600)
        raw = s1.issue(
            workspace_id="ws-main",
            project_id="p",
            run_id="r",
            scopes=("s",),
        )
        session1 = s1.redeem(raw, workspace_id="ws-main")
        session_id = session1.session_id
        s1.close()

        s2 = BrowserSessionGrantStore(db_path=str(db), ttl_seconds=3600)
        assert s2._session_count() == 1
        assert s2._session_exists(session_id)
        s2.close()


class TestNoNetwork:
    """Criterion 15: tests do not use network or real credentials."""

    def test_all_operations_offline(
        self, store: BrowserSessionGrantStore,
    ):
        """Create grant, redeem, revoke -- all succeed offline."""
        raw = store.issue(
            workspace_id="ws-offline",
            project_id="proj-off",
            run_id="run-0",
            scopes=("offline",),
        )
        session = store.redeem(raw, workspace_id="ws-offline")
        assert session.session_id
        assert store.revoke_session(session.session_id) is True


class TestScopeIntegrity:
    """Criterion 16 check: scopes are a tuple on session."""

    def test_scopes_is_tuple_on_session(
        self, store: BrowserSessionGrantStore, grant: str,
    ):
        """Session.scopes is a tuple (immutable, hashable)."""
        session = store.redeem(grant, workspace_id="ws-main")
        assert isinstance(session.scopes, tuple)


class TestDeliveryResponse:
    """Structures for cookie/header recommendations."""

    def test_session_cookie_renders_set_cookie_header(self):
        """Set-Cookie header string is correctly formatted."""
        cookie = SessionCookie.from_session_value(
            session_id="test-session-id",
            max_age=900,
        )
        header = cookie.to_set_cookie_header()
        assert "test-session-id" in header
        assert "HttpOnly" in header
        assert "SameSite=Lax" in header
        assert "Max-Age=900" in header
        assert "Path=/" in header

    def test_browser_session_response_construction(self):
        """BrowserSessionResponse builds correctly from session data."""
        response = BrowserSessionResponse.from_session(
            session_id="test-session-id",
            max_age=900,
            expires_at_iso="2026-01-01T00:00:00+00:00",
        )
        assert response.session_id == "test-session-id"
        assert response.cookie.value == "test-session-id"
        assert response.header.value == "test-session-id"
        assert response.expires_at == "2026-01-01T00:00:00+00:00"

    def test_session_header_defaults(self):
        """SessionHeader uses default name X-Browser-Session-Id."""
        header = SessionHeader.from_session_value("sid-123")
        assert header.name == "X-Browser-Session-Id"
        assert header.value == "sid-123"


class TestInputValidation:
    """Input validation edge cases."""

    def test_empty_workspace_id_raises_value_error(
        self, store: BrowserSessionGrantStore,
    ):
        with pytest.raises(ValueError, match="workspace_id is required"):
            store.issue(
                workspace_id="",
                project_id="p",
                run_id="r",
                scopes=("s",),
            )

    def test_empty_project_id_raises_value_error(
        self, store: BrowserSessionGrantStore,
    ):
        with pytest.raises(ValueError, match="project_id is required"):
            store.issue(
                workspace_id="ws",
                project_id="",
                run_id="r",
                scopes=("s",),
            )

    def test_empty_run_id_raises_value_error(
        self, store: BrowserSessionGrantStore,
    ):
        with pytest.raises(ValueError, match="run_id is required"):
            store.issue(
                workspace_id="ws",
                project_id="p",
                run_id="",
                scopes=("s",),
            )

    def test_empty_scopes_raises_value_error(
        self, store: BrowserSessionGrantStore,
    ):
        with pytest.raises(ValueError, match="scopes must be non-empty"):
            store.issue(
                workspace_id="ws",
                project_id="p",
                run_id="r",
                scopes=(),
            )

    def test_purge_expired_removes_stale_grants(self, tmp_path: Path):
        """purge_expired() removes expired grants."""
        store = BrowserSessionGrantStore(
            db_path=str(tmp_path / "purge.db"),
            ttl_seconds=0,
        )
        store.issue(
            workspace_id="ws",
            project_id="p",
            run_id="r",
            scopes=("s",),
        )
        assert store._grant_count() == 1
        purged = store.purge_expired()
        assert purged >= 1
        assert store._grant_count() == 0
