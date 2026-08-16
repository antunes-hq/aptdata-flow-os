"""Browser session grant store — hash-only, one-shot, TTL-bounded tokens.

Design principles:
  - Every raw grant is a 64-character hex string from 32 bytes of os.urandom().
  - The raw value is returned *once* and NEVER persisted.
  - The store persists sha256(raw_grant) as the lookup key.
  - Redemption is one-shot: the grant row is deleted atomically and a
    BrowserSession row is inserted in its place.
  - All secret comparisons use hmac.compare_digest for constant-time.
  - repr(), exception messages, and log strings never contain the raw grant.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import sqlite3
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions — deterministic, sanitised, never leak raw grant
# ---------------------------------------------------------------------------


class BrowserSessionGrantError(Exception):
    """Base for all grant-related errors. Payload is sanitised."""


class GrantNotFoundError(BrowserSessionGrantError):
    """Grant hash not found in store (invalid, already consumed, or never issued)."""


class GrantRedeemedError(BrowserSessionGrantError):
    """Grant was already redeemed (one-shot violation)."""


class GrantExpiredError(BrowserSessionGrantError):
    """Grant or session has exceeded its TTL."""


class GrantRevokedError(BrowserSessionGrantError):
    """Grant or session was explicitly revoked."""


class GrantWorkspaceError(BrowserSessionGrantError):
    """Workspace mismatch between the grant and the redeem request."""


class GrantRunError(BrowserSessionGrantError):
    """Run mismatch between the grant and the redeem request."""


class GrantScopeError(BrowserSessionGrantError):
    """One or more required scopes are not covered by this grant."""


class SessionExpiredError(BrowserSessionGrantError):
    """Session has expired and is no longer valid."""


class SessionNotFoundError(BrowserSessionGrantError):
    """Session ID not found in store."""


class SessionRevokedError(BrowserSessionGrantError):
    """Session was explicitly revoked."""


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------


@dataclass
class BrowserSession:
    """Authorised browser session obtained by redeeming a grant.

    All fields are safe to log or serialise — the raw grant is never
    part of this object.
    """

    session_id: str
    workspace_id: str
    project_id: str
    run_id: str
    scopes: tuple[str, ...]
    created_at: datetime
    expires_at: datetime

    def __repr__(self) -> str:
        return (
            f"BrowserSession(session_id={self.session_id!r}, "
            f"workspace_id={self.workspace_id!r}, "
            f"project_id={self.project_id!r}, "
            f"run_id={self.run_id!r}, "
            f"scopes={self.scopes!r}, "
            f"expires_at={self.expires_at.isoformat()!r})"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_DEFAULT_TTL: int = 900  # 15 minutes
_REDACTED: str = "<grant-redacted>"


def _grant_hash(raw_grant: str) -> str:
    """SHA-256 hash of the raw grant. Safe to persist and log."""
    return hashlib.sha256(raw_grant.encode("utf-8")).hexdigest()


def _new_raw_grant() -> str:
    """Generate a cryptographically random 64-character hex grant."""
    raw = __import__("os").urandom(32)
    return hashlib.sha256(
        hashlib.sha256(hashlib.sha256(raw).digest()).digest()
    ).hexdigest()


def _now_ts() -> int:
    """Current UTC time as an integer epoch second (for SQLite)."""
    return int(time.time())


# ---------------------------------------------------------------------------
# SQLite-backed store
# ---------------------------------------------------------------------------


class BrowserSessionGrantStore:
    """SQLite-backed store for browser session grants.

    Usage::

        store = BrowserSessionGrantStore(db_path="/tmp/grants.db")
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=("capture:read", "run:view"),
        )
        session = store.redeem(raw, workspace_id="ws-main")
        store.revoke(raw)
        store.close()

    Thread-safety: SQLite in WAL mode provides serialized writes; for
    multi-process scenarios each process should open its own instance.
    """

    def __init__(self, db_path: str, ttl_seconds: int = _DEFAULT_TTL) -> None:
        self._db_path = db_path
        self._ttl_seconds = ttl_seconds
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._init_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        """Create tables if they don't exist."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS browser_session_grants (
                grant_hash     TEXT PRIMARY KEY,
                session_id     TEXT NOT NULL,
                workspace_id   TEXT NOT NULL,
                project_id     TEXT NOT NULL,
                run_id         TEXT NOT NULL,
                scopes         TEXT NOT NULL,  -- comma-separated
                telegram_user_id TEXT,
                created_at     INTEGER NOT NULL,  -- epoch seconds
                expires_at     INTEGER NOT NULL,  -- epoch seconds
                revoked        INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS browser_sessions (
                session_id     TEXT PRIMARY KEY,
                workspace_id   TEXT NOT NULL,
                project_id     TEXT NOT NULL,
                run_id         TEXT NOT NULL,
                scopes         TEXT NOT NULL,
                created_at     INTEGER NOT NULL,
                expires_at     INTEGER NOT NULL,
                revoked        INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_grants_expires
                ON browser_session_grants(expires_at);
            CREATE INDEX IF NOT EXISTS idx_sessions_expires
                ON browser_sessions(expires_at);
        """)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def issue(
        self,
        *,
        workspace_id: str,
        project_id: str,
        run_id: str,
        scopes: Sequence[str],
        telegram_user_id: str | None = None,
        ttl_seconds: int | None = None,
    ) -> str:
        """Issue a new browser session grant.

        Returns the raw grant string. The raw value is returned **once**
        and is never persisted — only its SHA-256 hash is stored.

        Raises:
            ValueError: if workspace_id, project_id, run_id are empty,
                        or scopes is empty.
        """
        if not workspace_id:
            raise ValueError("workspace_id is required")
        if not project_id:
            raise ValueError("project_id is required")
        if not run_id:
            raise ValueError("run_id is required")
        if not scopes:
            raise ValueError("scopes must be non-empty")

        raw = _new_raw_grant()
        ghash = _grant_hash(raw)
        session_id = str(uuid4())
        now_ts = _now_ts()
        effective_ttl = ttl_seconds if ttl_seconds is not None else self._ttl_seconds
        expires_at = now_ts + effective_ttl
        scopes_str = ",".join(scopes)

        try:
            self._conn.execute(
                """INSERT INTO browser_session_grants
                   (grant_hash, session_id, workspace_id, project_id, run_id,
                    scopes, telegram_user_id, created_at, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ghash, session_id, workspace_id, project_id, run_id,
                    scopes_str, telegram_user_id, now_ts, expires_at,
                ),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            # Extremely unlikely hash collision — retry once
            return self.issue(
                workspace_id=workspace_id,
                project_id=project_id,
                run_id=run_id,
                scopes=scopes,
                telegram_user_id=telegram_user_id,
                ttl_seconds=effective_ttl,
            )

        logger.info(
            "Grant issued: session_id=%s workspace=%s project=%s run=%s",
            session_id, workspace_id, project_id, run_id,
        )
        return raw

    def redeem(
        self,
        raw_grant: str,
        *,
        workspace_id: str,
        run_id: str | None = None,
        required_scopes: Sequence[str] = (),
    ) -> BrowserSession:
        """Redeem a raw grant for an authorised browser session.

        This is **one-shot**: a successful redemption deletes the grant
        row and creates a session row atomically.

        Args:
            raw_grant: The raw grant string returned by issue().
            workspace_id: Must match the grant's workspace.
            run_id: If provided, must match the grant's run.
            required_scopes: All of these scopes must be present.

        Returns:
            A BrowserSession with metadata (never the raw grant).

        Raises:
            GrantNotFoundError: Grant hash not found.
            GrantExpiredError: Grant has expired.
            GrantRevokedError: Grant was revoked.
            GrantRedeemedError: Grant was already consumed (one-shot).
            GrantWorkspaceError: workspace_id does not match.
            GrantRunError: run_id does not match.
            GrantScopeError: required_scopes not satisfied.
        """
        ghash = _grant_hash(raw_grant)
        now_ts = _now_ts()

        # BEGIN IMMEDIATE acquires a write lock upfront, preventing
        # deadlocks in concurrent scenarios. All code paths below either
        # COMMIT (on success or grant-consuming failure) or ROLLBACK (on
        # validation errors) before returning.
        self._conn.execute("BEGIN IMMEDIATE;")
        try:
            row = self._conn.execute(
                "SELECT * FROM browser_session_grants WHERE grant_hash = ?",
                (ghash,),
            ).fetchone()

            if row is None:
                self._conn.execute("ROLLBACK;")
                raise GrantNotFoundError("Grant not found or already consumed")

            # Check expiry
            if now_ts >= row["expires_at"]:
                self._delete_grant(row["grant_hash"])
                self._conn.commit()
                raise GrantExpiredError("Grant has expired")

            # Check revocation
            if row["revoked"]:
                self._delete_grant(row["grant_hash"])
                self._conn.commit()
                raise GrantRevokedError("Grant has been revoked")

            # Check workspace
            if not hmac.compare_digest(str(row["workspace_id"]), str(workspace_id)):
                self._conn.execute("ROLLBACK;")
                raise GrantWorkspaceError(
                    f"Workspace mismatch: expected {row['workspace_id']!r}"
                )

            # Check run
            if run_id is not None and not hmac.compare_digest(
                str(row["run_id"]), str(run_id)
            ):
                self._conn.execute("ROLLBACK;")
                raise GrantRunError(
                    f"Run mismatch: expected {row['run_id']!r}"
                )

            # Check scopes
            grant_scopes = set(row["scopes"].split(",")) if row["scopes"] else set()
            required = set(required_scopes)
            if required and not required.issubset(grant_scopes):
                missing = required - grant_scopes
                self._conn.execute("ROLLBACK;")
                raise GrantScopeError(f"Missing required scopes: {sorted(missing)}")

            # One-shot: delete the grant, insert the session
            self._conn.execute(
                "DELETE FROM browser_session_grants WHERE grant_hash = ?",
                (ghash,),
            )

            session_id = row["session_id"]
            session_ttl = self._ttl_seconds
            session_expires = now_ts + session_ttl
            workspace_id_from_row = row["workspace_id"]
            project_id_from_row = row["project_id"]
            run_id_from_row = row["run_id"]
            scopes_str_from_row = row["scopes"]
            created_at_from_row = row["created_at"]

            self._conn.execute(
                """INSERT INTO browser_sessions
                   (session_id, workspace_id, project_id, run_id,
                    scopes, created_at, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    workspace_id_from_row,
                    project_id_from_row,
                    run_id_from_row,
                    scopes_str_from_row,
                    created_at_from_row,
                    session_expires,
                ),
            )
            self._conn.commit()

            scopes_tuple = (
                tuple(scopes_str_from_row.split(","))
                if scopes_str_from_row
                else ()
            )
            logger.info(
                "Grant redeemed: session_id=%s workspace=%s",
                session_id, workspace_id,
            )
            return BrowserSession(
                session_id=session_id,
                workspace_id=workspace_id_from_row,
                project_id=project_id_from_row,
                run_id=run_id_from_row,
                scopes=scopes_tuple,
                created_at=datetime.fromtimestamp(
                    created_at_from_row, tz=timezone.utc
                ),
                expires_at=datetime.fromtimestamp(
                    session_expires, tz=timezone.utc
                ),
            )
        except (
            GrantNotFoundError,
            GrantWorkspaceError,
            GrantRunError,
            GrantScopeError,
            GrantExpiredError,
            GrantRevokedError,
        ):
            # These exceptions already committed or rolled back the
            # transaction above. Just re-raise.
            raise
        except Exception:
            # Unexpected error — rollback to leave store consistent,
            # then re-raise.
            self._conn.execute("ROLLBACK;")
            raise

    def get_session(
        self,
        session_id: str,
        *,
        workspace_id: str,
        run_id: str | None = None,
        required_scopes: Sequence[str] = (),
    ) -> BrowserSession:
        """Retrieve and validate an existing browser session.

        Re-validates workspace, run, scopes, expiry and revocation at
        lookup time — the caller must pass the expected context so that
        a compromised session_id cannot be used outside its bindings.

        Args:
            session_id: The opaque session identifier.
            workspace_id: Must match the session's workspace.
            run_id: If provided, must match the session's run.
            required_scopes: All of these scopes must be present.

        Returns:
            A BrowserSession with metadata.

        Raises:
            SessionNotFoundError: session_id does not exist.
            SessionExpiredError: Session has expired.
            SessionRevokedError: Session was revoked.
            GrantWorkspaceError: workspace_id does not match.
            GrantRunError: run_id does not match.
            GrantScopeError: required_scopes not satisfied.
        """
        row = self._conn.execute(
            "SELECT * FROM browser_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()

        if row is None:
            raise SessionNotFoundError("Session not found")

        now_ts = _now_ts()

        # Check expiry
        if now_ts >= row["expires_at"]:
            raise SessionExpiredError("Session has expired")

        # Check revocation
        if row["revoked"]:
            raise SessionRevokedError("Session has been revoked")

        # Check workspace
        if not hmac.compare_digest(str(row["workspace_id"]), str(workspace_id)):
            raise GrantWorkspaceError(
                f"Workspace mismatch: expected {row['workspace_id']!r}"
            )

        # Check run
        if run_id is not None and not hmac.compare_digest(
            str(row["run_id"]), str(run_id)
        ):
            raise GrantRunError(
                f"Run mismatch: expected {row['run_id']!r}"
            )

        # Check scopes
        session_scopes = set(row["scopes"].split(",")) if row["scopes"] else set()
        required = set(required_scopes)
        if required and not required.issubset(session_scopes):
            missing = required - session_scopes
            raise GrantScopeError(f"Missing required scopes: {sorted(missing)}")

        scopes_tuple = (
            tuple(row["scopes"].split(","))
            if row["scopes"]
            else ()
        )
        return BrowserSession(
            session_id=row["session_id"],
            workspace_id=row["workspace_id"],
            project_id=row["project_id"],
            run_id=row["run_id"],
            scopes=scopes_tuple,
            created_at=datetime.fromtimestamp(row["created_at"], tz=timezone.utc),
            expires_at=datetime.fromtimestamp(row["expires_at"], tz=timezone.utc),
        )

    def revoke(self, raw_grant: str) -> bool:
        """Revoke a grant by its raw value. Returns True if revoked."""
        ghash = _grant_hash(raw_grant)
        cursor = self._conn.execute(
            "UPDATE browser_session_grants SET revoked = 1 "
            "WHERE grant_hash = ? AND revoked = 0",
            (ghash,),
        )
        self._conn.commit()
        affected = cursor.rowcount > 0
        if affected:
            logger.info("Grant revoked (hash=%s...)", ghash[:8])
        return affected

    def revoke_session(self, session_id: str) -> bool:
        """Revoke an active session by its session_id. Returns True if revoked."""
        cursor = self._conn.execute(
            "UPDATE browser_sessions SET revoked = 1 "
            "WHERE session_id = ? AND revoked = 0",
            (session_id,),
        )
        self._conn.commit()
        affected = cursor.rowcount > 0
        if affected:
            logger.info("Session revoked: %s", session_id)
        return affected

    # ------------------------------------------------------------------
    # Administrative helpers (safe, no raw grant leakage)
    # ------------------------------------------------------------------

    def _delete_grant(self, grant_hash: str) -> None:
        """Delete a grant row by its hash."""
        self._conn.execute(
            "DELETE FROM browser_session_grants WHERE grant_hash = ?",
            (grant_hash,),
        )

    def purge_expired(self) -> int:
        """Delete all expired grants from the store.

        Returns the number of purged rows.
        """
        now_ts = _now_ts()
        cursor = self._conn.execute(
            "DELETE FROM browser_session_grants WHERE expires_at <= ?",
            (now_ts,),
        )
        self._conn.commit()
        return cursor.rowcount

    def close(self) -> None:
        """Close the database connection. Idempotent."""
        if self._conn:
            self._conn.close()
            self._conn = None  # type: ignore[assignment]

    def __enter__(self) -> BrowserSessionGrantStore:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Test helpers (NOT part of the public contract; exposed for
    # acceptance-criterion verification)
    # ------------------------------------------------------------------

    def _grant_count(self) -> int:
        """Number of grant rows in the store. Test helper."""
        row = self._conn.execute(
            "SELECT COUNT(*) AS cnt FROM browser_session_grants"
        ).fetchone()
        return row["cnt"] if row else 0

    def _session_count(self) -> int:
        """Number of session rows in the store. Test helper."""
        row = self._conn.execute(
            "SELECT COUNT(*) AS cnt FROM browser_sessions"
        ).fetchone()
        return row["cnt"] if row else 0

    def _grant_hash_exists(self, raw_grant: str) -> bool:
        """Check if a grant's hash exists in the store. Test helper."""
        ghash = _grant_hash(raw_grant)
        row = self._conn.execute(
            "SELECT 1 FROM browser_session_grants WHERE grant_hash = ?",
            (ghash,),
        ).fetchone()
        return row is not None

    def _session_exists(self, session_id: str) -> bool:
        """Check if a session exists. Test helper."""
        row = self._conn.execute(
            "SELECT 1 FROM browser_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return row is not None

    def _find_session_by_grant(self, raw_grant: str) -> str | None:
        """Find session_id for a given grant. Only works before redeem.

        After redeem the grant row is gone; this returns None.
        Test helper.
        """
        ghash = _grant_hash(raw_grant)
        row = self._conn.execute(
            "SELECT session_id FROM browser_session_grants WHERE grant_hash = ?",
            (ghash,),
        ).fetchone()
        return str(row["session_id"]) if row else None

    def _raw_grant_in_store(self, raw_grant: str) -> bool:
        """Verify no raw grant string appears anywhere in the DB.

        Scans all TEXT columns in grants and sessions tables.
        """
        # Scan all text columns in browser_session_grants
        rows = self._conn.execute(
            "SELECT grant_hash, session_id, workspace_id, project_id, "
            "run_id, scopes, telegram_user_id "
            "FROM browser_session_grants"
        ).fetchall()
        for row in rows:
            for col in row:
                if isinstance(col, str) and raw_grant in col:
                    return True

        # Scan all text columns in browser_sessions
        rows2 = self._conn.execute(
            "SELECT session_id, workspace_id, project_id, run_id, scopes "
            "FROM browser_sessions"
        ).fetchall()
        for row in rows2:
            for col in row:
                if isinstance(col, str) and raw_grant in col:
                    return True

        return False
