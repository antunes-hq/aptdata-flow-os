"""Telegram notifier — consumes FlowEvent outbox messages and delivers via Telegram.

Why this exists:
- Read-only notifier that consumes claimed OutboxMessage rows (channel="telegram"),
  formats them as short human text, sends via an injectable HTTP client, and
  marks the outbox row as sent or failed.
- No conversation engine, no polling, no approval callbacks.
- The Telegram client is injectable (protocol) so tests never hit the network.

Naming conventions follow aptdata/delivery/outbox.py — names are self-explanatory
to someone unfamiliar with the codebase. Reuses FlowEvent and DurableOutbox
without duplicating ConversationEngine or TelegramTransport.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from aptdata.delivery.outbox import DurableOutbox, OutboxStatus
from aptdata.events.models import FlowEvent

logger = logging.getLogger(__name__)

# Maximum Telegram message length (Telegram's limit is 4096 UTF-8 chars)
_MAX_MESSAGE_LENGTH: int = 4096

# Patterns to redact from messages — never leak tokens or secrets
_REDACT_PATTERNS: list[re.Pattern] = [
    re.compile(r"bearer\s+\S+", re.IGNORECASE),
    re.compile(r"api[_-]?key[=:]\s*\S+", re.IGNORECASE),
    re.compile(r"token[=:]\s*\S+", re.IGNORECASE),
    re.compile(r"secret[=:]\s*\S+", re.IGNORECASE),
    re.compile(r"authorization:\s*\S+", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Injectable Telegram client protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class TelegramClient(Protocol):
    """Protocol for an injectable Telegram HTTP client.

    Implementations must accept at least ``chat_id`` and ``text``.
    Additional keyword arguments are passed as Telegram API parameters
    (e.g. ``disable_web_page_preview``).

    Must **not** raise on transport errors — return ``False`` instead
    so the notifier can mark the outbox row as failed gracefully.
    """

    def send_message(
        self,
        chat_id: str | int,
        text: str,
        **kwargs: Any,
    ) -> bool:
        """Send a message to a Telegram chat.

        Returns ``True`` on success (HTTP 2xx), ``False`` on failure.
        """
        ...


# ---------------------------------------------------------------------------
# Default HTTP client (backed by httpx, an existing optional dep)
# ---------------------------------------------------------------------------


class HttpxTelegramClient:
    """Default Telegram client backed by httpx.

    Token is required at construction (from env or explicit config).
    Never logs or stores the token in event payloads or formatted text.
    Uses a configurable timeout to avoid hanging on network issues.

    Usage::

        client = HttpxTelegramClient(token="123:ABC")
        ok = client.send_message(chat_id=-100123, text="Hello")

    Or with env variable::

        client = HttpxTelegramClient(token_env="MY_BOT_TOKEN")
    """

    API_BASE = "https://api.telegram.org"

    def __init__(
        self,
        token: str | None = None,
        *,
        token_env: str = "TELEGRAM_BOT_TOKEN",
        api_base: str = API_BASE,
        timeout: float = 15.0,
    ) -> None:
        if token is None:
            import os  # noqa: PLC0415 — lazy import

            token = os.environ.get(token_env)
            if not token:
                raise ValueError(
                    f"Telegram token not provided and {token_env} is not set"
                )
        self._token = token
        self._api_base = api_base.rstrip("/")
        self._timeout = timeout

    def send_message(
        self,
        chat_id: str | int,
        text: str,
        **kwargs: Any,
    ) -> bool:
        import httpx  # noqa: PLC0415 — lazy import

        url = f"{self._api_base}/bot{self._token}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
        }
        payload.update(kwargs)
        try:
            resp = httpx.post(url, json=payload, timeout=self._timeout)
            return resp.is_success
        except Exception:
            logger.exception("Telegram send_message failed")
            return False


# ---------------------------------------------------------------------------
# Structured result
# ---------------------------------------------------------------------------


@dataclass
class NotifierResult:
    """Structured result from processing a single outbox message.

    Attributes:
        message_id: The outbox message ID.
        event_id: The FlowEvent ID this delivery relates to.
        event_type: The FlowEvent event_type (e.g. "run.started").
        status: Final outbox status after processing (SENT or FAILED).
        error: Sanitized error message if status is FAILED, else None.
    """

    message_id: str
    event_id: str
    event_type: str
    status: OutboxStatus
    error: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def safe_redact(text: str) -> str:
    """Redact bearer tokens, API keys, and secrets from text.

    Replaces known sensitive patterns with ``[REDACTED]`` so tokens
    never appear in formatted messages, logs, or stored error strings.
    """
    for pattern in _REDACT_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def _truncate(text: str, max_length: int = _MAX_MESSAGE_LENGTH) -> str:
    """Truncate *text* to *max_length* chars, appending ``…`` if cut."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 1] + "…"


# ---------------------------------------------------------------------------
# Event formatter
# ---------------------------------------------------------------------------


def format_flow_event(event: FlowEvent) -> str:
    """Format a FlowEvent into short human-readable Telegram text.

    Returns a string bounded by ``_MAX_MESSAGE_LENGTH`` with secrets
    redacted via :func:`safe_redact`.

    Format by event_type:

    * ``run.started`` — short start notice
    * ``stage.completed`` — stage summary
    * ``checkpoint`` — checkpoint with next step
    * ``approval.required`` — approval prompt with action/risk/expiry (never token)
    * ``run.blocked`` — blockage notice
    * ``run.completed`` — completion with result and evidence refs
    * *other* — generic fallback
    """
    summary = event.human_summary or ""
    project = f"{event.workspace_id}/{event.project_id}"
    run_id = event.run_id

    event_type = event.event_type
    if event_type == "run.started":
        lines = [
            "🚀 *Run Started*",
            f"`{project}` · `{run_id}`",
            "",
            summary,
        ]
    elif event_type == "stage.completed":
        stage = event.stage_id or "?"
        lines = [
            "✅ *Stage Completed*",
            f"`{project}` · `{run_id}`",
            f"Stage: `{stage}`",
            "",
            summary,
        ]
    elif event_type == "checkpoint":
        next_step = event.next_action or "—"
        lines = [
            "📍 *Checkpoint*",
            f"`{project}` · `{run_id}`",
            "",
            summary,
            "",
            f"Next: {next_step}",
        ]
    elif event_type == "approval.required":
        meta = event.metadata or {}
        risk = meta.get("risk", "?")
        expires = meta.get("expires_at", "—")
        lines = [
            "⚠️ *Approval Required*",
            f"`{project}` · `{run_id}`",
            "",
            summary,
            "",
            f"Action: {event.next_action or '—'}",
            f"Risk: {risk}",
            f"Expires: {expires}",
        ]
    elif event_type == "run.blocked":
        lines = [
            "⛔ *Run Blocked*",
            f"`{project}` · `{run_id}`",
            "",
            summary,
        ]
    elif event_type == "run.completed":
        refs = event.evidence_refs or []
        refs_str = " | ".join(refs) if refs else "—"
        lines = [
            "🏁 *Run Completed*",
            f"`{project}` · `{run_id}`",
            "",
            summary,
            "",
            f"Evidence: {refs_str}",
        ]
    else:
        # Fallback for unknown event types
        lines = [
            f"📬 *Event: {event_type}*",
            f"`{project}` · `{run_id}`",
            "",
            summary,
        ]

    text = "\n".join(lines)
    text = safe_redact(text)
    return _truncate(text)


# ---------------------------------------------------------------------------
# Notifier
# ---------------------------------------------------------------------------


class TelegramNotifier:
    """Consumes Telegram outbox messages and delivers via an injectable client.

    Usage::

        notifier = TelegramNotifier(client=my_client, chat_id=-100123)
        results = notifier.notify(outbox)
        for r in results:
            print(f"{r.event_type}: {r.status.value}")
    """

    def __init__(
        self,
        client: TelegramClient,
        chat_id: str | int,
    ) -> None:
        self._client = client
        self._chat_id = chat_id

    def notify(
        self,
        outbox: DurableOutbox,
        *,
        limit: int = 10,
    ) -> list[NotifierResult]:
        """Claim pending Telegram outbox messages and deliver them.

        For each claimed message whose channel is ``"telegram"``:

        1. Deserialize the ``FlowEvent`` from ``payload_json``.
        2. Format as human-readable Telegram text via :func:`format_flow_event`.
        3. Send via the injectable *client* to the configured *chat_id*.
        4. On success → ``outbox.mark_sent(message_id)``.
        5. On failure → ``outbox.mark_failed(message_id, error)`` with sanitized error.

        Messages for other channels are left in ``pending`` — their attempts
        counter is bumped but they are not processed here.

        Returns:
            A list of :class:`NotifierResult` — one per processed message.
            Never raises; errors are captured in the result and stored in the outbox.
        """
        results: list[NotifierResult] = []

        messages = outbox.claim_pending(limit=limit)
        for msg in messages:
            if msg.channel != "telegram":
                continue

            result = self._process_one(outbox, msg)
            results.append(result)

        return results

    def _process_one(
        self,
        outbox: DurableOutbox,
        msg: Any,
    ) -> NotifierResult:
        """Process a single outbox message.

        This is a separate method for testability.
        """
        # --- Parse the FlowEvent from payload_json ---
        try:
            event = FlowEvent.model_validate_json(msg.payload_json)
        except Exception as exc:
            err = safe_redact(str(exc))
            err = _truncate(err, 512)
            outbox.mark_failed(msg.message_id, err)
            return NotifierResult(
                message_id=msg.message_id,
                event_id=msg.event_id,
                event_type="unknown",
                status=OutboxStatus.FAILED,
                error=err,
            )

        # --- Format the event text ---
        text = format_flow_event(event)

        # --- Send via client ---
        try:
            sent = self._client.send_message(
                self._chat_id,
                text,
                disable_web_page_preview=True,
            )
        except Exception as exc:
            # Client raised (shouldn't happen per protocol, but be defensive)
            err = safe_redact(str(exc))
            err = _truncate(err, 512)
            outbox.mark_failed(msg.message_id, err)
            return NotifierResult(
                message_id=msg.message_id,
                event_id=msg.event_id,
                event_type=event.event_type,
                status=OutboxStatus.FAILED,
                error=err,
            )

        if sent:
            outbox.mark_sent(msg.message_id)
            return NotifierResult(
                message_id=msg.message_id,
                event_id=msg.event_id,
                event_type=event.event_type,
                status=OutboxStatus.SENT,
            )

        err = "Telegram client returned failure (HTTP non-2xx)"
        outbox.mark_failed(msg.message_id, err)
        return NotifierResult(
            message_id=msg.message_id,
            event_id=msg.event_id,
            event_type=event.event_type,
            status=OutboxStatus.FAILED,
            error=err,
        )
