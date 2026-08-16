"""HTTP-friendly response structures for browser session grants.

These models describe how a browser session should be conveyed to the
client (cookie or header). No HTTP server is required — the structures
are pure data that can be rendered by any transport.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class SessionCookie:
    """Recommendation for a session cookie.

    Usage::

        cookie = SessionCookie.from_session(session)
        # Then set Set-Cookie header in whatever HTTP layer exists.
    """

    name: str = "browser_session_id"
    value: str = ""
    path: str = "/"
    domain: str = ""  # empty = no Domain attribute (host-only cookie)
    httponly: bool = True
    samesite: Literal["Lax", "Strict", "None"] = "Lax"
    secure: bool = False  # True in production over HTTPS
    max_age: int = 900

    @classmethod
    def from_session_value(
        cls,
        session_id: str,
        max_age: int,
        *,
        secure: bool = False,
        domain: str = "",
    ) -> SessionCookie:
        return cls(
            value=session_id,
            max_age=max_age,
            secure=secure,
            domain=domain,
        )

    def to_set_cookie_header(self) -> str:
        """Return the ``Set-Cookie`` header string.

        Example output without Domain::

            browser_session_id=abc...; Path=/; HttpOnly; SameSite=Lax

        Example output with Domain::

            browser_session_id=abc...; Path=/; Domain=.example.com; HttpOnly; SameSite=Lax
        """
        parts = [f"{self.name}={self.value}", f"Path={self.path}"]
        if self.domain:
            parts.append(f"Domain={self.domain}")
        if self.httponly:
            parts.append("HttpOnly")
        if self.secure:
            parts.append("Secure")
        parts.append(f"SameSite={self.samesite}")
        parts.append(f"Max-Age={self.max_age}")
        return "; ".join(parts)


@dataclass
class SessionHeader:
    """Recommendation for an explicit session header.

    Some clients (e.g. Server-Sent Events) prefer a header over a cookie.
    """

    name: str = "X-Browser-Session-Id"
    value: str = ""

    @classmethod
    def from_session_value(cls, session_id: str, /) -> SessionHeader:
        return cls(value=session_id)


@dataclass
class BrowserSessionResponse:
    """Complete response envelope for a successful grant redemption.

    Contains both the session metadata and transport recommendations.
    """

    session_id: str
    cookie: SessionCookie = field(default_factory=SessionCookie)
    header: SessionHeader = field(default_factory=SessionHeader)
    expires_at: str = ""

    @classmethod
    def from_session(
        cls,
        session_id: str,
        max_age: int,
        expires_at_iso: str,
        *,
        secure: bool = False,
    ) -> BrowserSessionResponse:
        return cls(
            session_id=session_id,
            cookie=SessionCookie.from_session_value(session_id, max_age, secure=secure),
            header=SessionHeader.from_session_value(session_id),
            expires_at=expires_at_iso,
        )

    def __repr__(self) -> str:
        return (
            f"BrowserSessionResponse("
            f"session_id={self.session_id!r}, "
            f"cookie={self.cookie.name}={self.cookie.value!r}, "
            f"header={self.header.name}={self.header.value!r})"
        )


__all__ = [
    "BrowserSessionResponse",
    "SessionCookie",
    "SessionHeader",
]
