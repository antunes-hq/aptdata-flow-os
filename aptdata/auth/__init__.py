"""Browser session grants — temporary, one-shot, hash-only tokens for browser access.

This module provides a local/testable grant store that enforces:
- Raw-grant hash-only storage (never persisted as plaintext)
- Cryptographic entropy via os.urandom()
- One-shot atomic redemption (no double-spend)
- TTL expiry
- Explicit revoke (by grant or session)
- Workspace / project / run binding
- Scope verification
- Constant-time comparisons
- Sanitized repr, exceptions, and logs

No network calls, real credentials, OAuth, or production dependencies.
"""

from __future__ import annotations

from aptdata.auth.session_grant import (
    BrowserSession,
    BrowserSessionGrantError,
    BrowserSessionGrantStore,
    GrantExpiredError,
    GrantNotFoundError,
    GrantRedeemedError,
    GrantRevokedError,
    GrantRunError,
    GrantScopeError,
    GrantWorkspaceError,
    SessionExpiredError,
)

__all__ = [
    "BrowserSession",
    "BrowserSessionGrantError",
    "BrowserSessionGrantStore",
    "GrantExpiredError",
    "GrantNotFoundError",
    "GrantRevokedError",
    "GrantRedeemedError",
    "GrantScopeError",
    "GrantWorkspaceError",
    "GrantRunError",
    "SessionExpiredError",
]
