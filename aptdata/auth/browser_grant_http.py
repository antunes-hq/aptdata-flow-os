"""Framework-neutral HTTP adapter for browser session grant redemption.

Exchanges an opaque grant (extracted from the URL path) for a browser
session cookie and a 303 redirect.  Pure request/response — no FastAPI,
Starlette, Flask, or ASGI dependency.  Web frameworks mount this adapter
later.

Design principles:
  - One-shot: the grant is consumed atomically on success.
  - The raw grant is never leaked in the response body, Location header,
    error messages, or log strings.
  - Mutable scopes (``approval:respond``, ``deploy``, etc.) are rejected
    even if the store would accept them.
  - Security headers (no-store, no-referrer, nosniff) are mandatory.
  - ``Secure`` attribute on the cookie is driven by an explicit policy
    passed at construction time.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from aptdata.auth.session_grant import BrowserSessionGrantStore
from aptdata.delivery.session_response import SessionCookie

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class BrowserGrantHttpError(Exception):
    """Base for HTTP-level grant errors.  Message is safe to expose."""


class GrantPathInvalid(BrowserGrantHttpError):
    """Grant in the URL path is missing or malformed."""


# ---------------------------------------------------------------------------
# Request / Response models (pure data, no framework dependency)
# ---------------------------------------------------------------------------


@dataclass
class BrowserGrantHttpRequest:
    """Inbound HTTP request abstraction.

    Fields mirror what a pure WSGI/ASGI environ provides, but without
    coupling to any framework.
    """

    method: str = "GET"
    path: str = ""
    query: Mapping[str, Sequence[str]] = field(default_factory=dict)
    headers: Mapping[str, str] = field(default_factory=dict)
    remote_address: str | None = None


@dataclass
class BrowserGrantHttpResponse:
    """Outbound HTTP response abstraction.

    ``headers`` is a plain dict of header-name → header-value.  Callers
    are responsible for serialising repeated headers such as ``Set-Cookie``;
    the adapter sets at most one ``Set-Cookie`` value.
    """

    status_code: int = 200
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""

    def __repr__(self) -> str:
        return (
            f"BrowserGrantHttpResponse(status_code={self.status_code}, "
            f"headers={len(self.headers)} keys, body={len(self.body)} bytes)"
        )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GRANT_PATH_RE = re.compile(r"^/access/([0-9a-f]{64})$")

# Scopes that are NEVER accepted via the browser grant HTTP boundary.
# The contract explicitly lists approval:respond, deploy, and mutable
# scopes; this set is intentionally comprehensive to catch future
# additions.
_MUTABLE_SCOPES: frozenset[str] = frozenset({
    "approval:respond",
    "deploy",
    "delete",
    "admin",
    "write",
    "capture:respond",
    "grant:issue",
    "config:write",
    "run:write",
    "run:cancel",
    "run:delete",
    "flow:write",
    "artifact:write",
})

# Scopes allowed by default per the contract.  The adapter rejects any
# grant whose scopes intersect _MUTABLE_SCOPES.  Non-mutable scopes not
# in this list are still permitted — the adapter only enforces the
# "no mutability" rule, not an allow-list.
_DEFAULT_ALLOWED_SCOPES: tuple[str, ...] = (
    "run:read",
    "flow:read",
    "artifact:read",
    "capture:read",
)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class BrowserGrantHttpAdapter:
    """HTTP adapter that redeems a one-shot grant and produces a 303 redirect.

    Usage::

        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            # expected_project and expected_run are optional — when omitted
            # the values stored in the grant are used, enabling a single
            # endpoint to serve grants for any project/run.
            expected_project=None,
            expected_run=None,
            secure=True,
            base_url="https://flow.example.com",
        )
        response = adapter.redeem_access_request(request)

    When ``expected_project`` and ``expected_run`` are both ``None``, the
    adapter uses the project and run encoded in the grant itself (dynamic
    resolution).  When either is given, the adapter validates the grant's
    value against it (static binding, same as before).

    The adapter is stateless with respect to the request — all persistent
    state lives in the ``BrowserSessionGrantStore``.
    """

    def __init__(
        self,
        store: BrowserSessionGrantStore,
        *,
        expected_workspace: str,
        expected_project: str | None = None,
        expected_run: str | None = None,
        secure: bool = False,
        base_url: str | None = None,
        cookie_domain: str = "",
    ) -> None:
        if not expected_workspace:
            raise ValueError("expected_workspace is required")

        self._store = store
        self._expected_workspace = expected_workspace
        self._expected_project = expected_project
        self._expected_run = expected_run
        self._secure = secure
        self._base_url = base_url
        self._cookie_domain = cookie_domain

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def redeem_access_request(
        self,
        request: BrowserGrantHttpRequest,
    ) -> BrowserGrantHttpResponse:
        """Handle an HTTP grant-redemption request.

        This method does **not** raise exceptions — every error path
        produces an appropriate HTTP response with a safe, short body.
        The only exception is from bug-level programming errors (e.g.
        a missing store), which propagate.
        """
        # --- 405: method check -------------------------------------------
        if request.method.upper() != "GET":
            return _error(405, "Method Not Allowed")

        # --- 400: grant extraction ----------------------------------------
        raw_grant = _extract_grant(request.path)
        if raw_grant is None:
            return _error(400, "Bad Request: missing or malformed grant")

        # --- 400: grant format check --------------------------------------
        if not _GRANT_PATH_RE.fullmatch(request.path):
            return _error(400, "Bad Request: invalid grant format")

        # --- Redeem -------------------------------------------------------
        try:
            session = self._store.redeem(
                raw_grant,
                workspace_id=self._expected_workspace,
                project_id=self._expected_project,
                run_id=self._expected_run,
            )
        except BrowserGrantHttpError:
            # This shouldn't happen in normal flow (the store raises its
            # own exception types), but catch it defensively.
            return _error(401, "Unauthorized: grant is invalid")
        except Exception as exc:
            # Store exceptions map to HTTP errors.  The catch is broad
            # because store.redeem raises multiple typed exceptions; we
            # map each one explicitly.
            return self._map_redeem_error(exc)

        # --- Scope mutability check ---------------------------------------
        if _has_mutable_scopes(session.scopes):
            return _error(403, "Forbidden: grant contains mutable scopes")

        # --- Build response -----------------------------------------------
        max_age = int(
            (session.expires_at - session.created_at).total_seconds()
        )
        max_age = max(max_age, 1)

        # Resolve project/run — when the adapter was constructed without
        # a static binding, use the values encoded in the grant itself.
        resolved_project = (
            self._expected_project
            if self._expected_project is not None
            else session.project_id
        )
        resolved_run = (
            self._expected_run
            if self._expected_run is not None
            else session.run_id
        )

        # Build the redirect Location — absolute when base_url is given,
        # relative otherwise.
        location = (
            f"/universe/{self._expected_workspace}"
            f"/{resolved_project}"
            f"/{resolved_run}"
        )
        if self._base_url:
            location = f"{self._base_url.rstrip('/')}{location}"

        cookie = SessionCookie.from_session_value(
            session.session_id,
            max_age=max_age,
            secure=self._secure,
            domain=self._cookie_domain,
        )
        set_cookie = cookie.to_set_cookie_header()

        headers = _security_headers()
        headers["Location"] = location
        headers["Set-Cookie"] = set_cookie

        logger.info(
            "Grant redeemed via HTTP: session_id=%s workspace=%s",
            session.session_id,
            self._expected_workspace,
        )

        return BrowserGrantHttpResponse(
            status_code=303,
            headers=headers,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _map_redeem_error(self, exc: Exception) -> BrowserGrantHttpResponse:
        """Map a store exception to an appropriate HTTP error response.

        The returned body is short, stable, and never contains the raw
        grant, its hash, a stack trace, or any infrastructure secret.
        """
        # Import here to avoid circular imports at module level.
        from aptdata.auth.session_grant import (  # type: ignore[import-untyped]
            GrantExpiredError,
            GrantNotFoundError,
            GrantProjectError,
            GrantRevokedError,
            GrantRunError,
            GrantScopeError,
            GrantWorkspaceError,
        )

        if isinstance(exc, GrantNotFoundError | GrantRevokedError):
            return _error(401, "Unauthorized: grant is invalid or revoked")
        if isinstance(exc, GrantExpiredError):
            return _error(401, "Unauthorized: grant has expired")
        if isinstance(exc, GrantWorkspaceError | GrantProjectError | GrantRunError):
            return _error(403, "Forbidden: context mismatch")
        if isinstance(exc, GrantScopeError):
            return _error(403, "Forbidden: scope mismatch")
        # Unexpected — log at debug level (not error, because we don't
        # know the severity) and return a generic 401.
        logger.debug("Unexpected redeem error type: %s", type(exc).__name__)
        return _error(401, "Unauthorized")


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _extract_grant(path: str) -> str | None:
    """Extract a 64-char hex grant from ``/access/<grant>``.

    Returns ``None`` when the path does not match or the grant segment
    is missing/malformed.
    """
    m = _GRANT_PATH_RE.match(path)
    return m.group(1) if m else None


def _has_mutable_scopes(scopes: tuple[str, ...]) -> bool:
    """Return ``True`` if any scope in *scopes* is considered mutable."""
    return bool(_MUTABLE_SCOPES.intersection(scopes))


def _error(status_code: int, message: str) -> BrowserGrantHttpResponse:
    """Build a safe error response.

    The body is a plain-text one-liner — no JSON framing, no raw grant,
    no hash, no stack trace.
    """
    body = message.encode("utf-8")
    return BrowserGrantHttpResponse(
        status_code=status_code,
        headers=_security_headers(),
        body=body,
    )


def _security_headers() -> dict[str, str]:
    """Return the set of mandatory security response headers."""
    return {
        "Cache-Control": "no-store",
        "Pragma": "no-cache",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
    }


__all__ = [
    "BrowserGrantHttpAdapter",
    "BrowserGrantHttpError",
    "BrowserGrantHttpRequest",
    "BrowserGrantHttpResponse",
    "GrantPathInvalid",
]
