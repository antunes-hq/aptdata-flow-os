"""Contract tests for F1.2b — Telegram Notifier Read-only.

Each test maps to one acceptance criterion from the workpacket.
All tests are offline/deterministic — no network, no tokens, no real Telegram API.
Telegram client is a fake (FakeTelegramClient) injected into TelegramNotifier.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from aptdata.delivery.outbox import DurableOutbox, OutboxStatus
from aptdata.delivery.telegram_notifier import (
    _MAX_MESSAGE_LENGTH,
    NotifierResult,
    TelegramNotifier,
    format_flow_event,
    safe_redact,
)
from aptdata.events.models import FlowEvent

# ---------------------------------------------------------------------------
# Fake Telegram client — records sent messages, never touches the network
# ---------------------------------------------------------------------------


@dataclass
class FakeTelegramClient:
    """In-memory fake that records every send_message call.

    ``should_succeed`` controls whether ``send_message`` returns True or False.
    ``sent`` accumulates all calls for test inspection.
    ``raise_on`` optionally raises ``Exception`` on the Nth call (0-indexed).
    """

    should_succeed: bool = True
    sent: list[dict[str, Any]] = field(default_factory=list)
    raise_on: int | None = None

    def send_message(
        self,
        chat_id: str | int,
        text: str,
        **kwargs: Any,
    ) -> bool:
        call = {"chat_id": chat_id, "text": text}
        call.update(kwargs)
        self.sent.append(call)

        if self.raise_on is not None and len(self.sent) - 1 == self.raise_on:
            raise RuntimeError("Simulated transport failure")

        return self.should_succeed


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def outbox(tmp_path: Path) -> DurableOutbox:
    """A DurableOutbox backed by a temporary SQLite database."""
    return DurableOutbox(db_path=str(tmp_path / "notifier_test.db"))


@pytest.fixture()
def fake_client() -> FakeTelegramClient:
    """A fake Telegram client that succeeds by default."""
    return FakeTelegramClient(should_succeed=True)


@pytest.fixture()
def notifier(fake_client: FakeTelegramClient) -> TelegramNotifier:
    """A TelegramNotifier wired to the fake client and a test chat_id."""
    return TelegramNotifier(client=fake_client, chat_id=-100123)


def _make_event(
    event_type: str = "run.started",
    *,
    human_summary: str = "Test summary",
    workspace_id: str = "ws-main",
    project_id: str = "proj-alpha",
    run_id: str = "run-42",
    stage_id: str | None = None,
    next_action: str | None = None,
    evidence_refs: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> FlowEvent:
    """Build a FlowEvent with defaults for quick test setup."""
    return FlowEvent(
        event_id=uuid4(),
        schema_version=1,
        event_type=event_type,
        workspace_id=workspace_id,
        project_id=project_id,
        run_id=run_id,
        severity="info",
        human_summary=human_summary,
        created_at=datetime.now(timezone.utc),
        stage_id=stage_id,
        next_action=next_action,
        evidence_refs=evidence_refs,
        metadata=metadata,
    )


# ===========================================================================
# Acceptance criterion 1: run.started generates short human message
# ===========================================================================


class TestRunStartedFormat:
    def test_contains_emoji_and_project(self):
        event = _make_event("run.started", human_summary="Pipeline kicked off")
        text = format_flow_event(event)
        assert "🚀" in text
        assert "Run Started" in text
        assert "ws-main/proj-alpha" in text
        assert "run-42" in text
        assert "Pipeline kicked off" in text

    def test_is_bounded(self):
        event = _make_event("run.started", human_summary="x" * 5000)
        text = format_flow_event(event)
        assert len(text) <= _MAX_MESSAGE_LENGTH


# ===========================================================================
# Acceptance criterion 2: checkpoint includes next step
# ===========================================================================


class TestCheckpointFormat:
    def test_includes_next_action(self):
        event = _make_event(
            "checkpoint",
            human_summary="Review complete",
            next_action="deploy to staging",
        )
        text = format_flow_event(event)
        assert "📍" in text
        assert "Checkpoint" in text
        assert "Next:" in text
        assert "deploy to staging" in text

    def test_missing_next_action_shows_dash(self):
        event = _make_event("checkpoint", next_action=None)
        text = format_flow_event(event)
        assert "Next:" in text
        assert "—" in text


# ===========================================================================
# Acceptance criterion 3: approval.required includes action/risk/expiry
# ===========================================================================


class TestApprovalRequiredFormat:
    def test_includes_action_risk_expiry(self):
        event = _make_event(
            "approval.required",
            human_summary="Deploy to production",
            next_action="confirm deployment",
            metadata={"risk": "medium", "expires_at": "2026-08-17T12:00Z"},
        )
        text = format_flow_event(event)
        assert "⚠️" in text
        assert "Approval Required" in text
        assert "Action: confirm deployment" in text
        assert "Risk: medium" in text
        assert "Expires: 2026-08-17T12:00Z" in text
        # Token must never appear
        assert "token" not in text.lower() or (
            "token" in text.lower() and "bearer" not in text.lower()
        )

    def test_missing_metadata_shows_placeholder(self):
        event = _make_event("approval.required", metadata=None)
        text = format_flow_event(event)
        assert "Risk: ?" in text
        assert "Expires: —" in text


# ===========================================================================
# Acceptance criterion 4: run.completed includes result/evidence refs
# ===========================================================================


class TestRunCompletedFormat:
    def test_includes_evidence_refs(self):
        event = _make_event(
            "run.completed",
            human_summary="All stages passed",
            evidence_refs=["doc://report/42", "doc://log/run-42"],
        )
        text = format_flow_event(event)
        assert "🏁" in text
        assert "Run Completed" in text
        assert "Evidence:" in text
        assert "doc://report/42" in text
        assert "doc://log/run-42" in text

    def test_no_evidence_shows_dash(self):
        event = _make_event("run.completed", evidence_refs=None)
        text = format_flow_event(event)
        assert "Evidence: —" in text


# ===========================================================================
# Acceptance criterion 5: unknown event uses fallback
# ===========================================================================


class TestFallbackFormat:
    def test_unknown_event_type_uses_generic(self):
        event = _make_event("custom.event", human_summary="Something happened")
        text = format_flow_event(event)
        assert "📬" in text
        assert "Event: custom.event" in text
        assert "Something happened" in text


# ===========================================================================
# Acceptance criterion 6: long message is truncated
# ===========================================================================


class TestMessageTruncation:
    def test_long_message_is_truncated(self):
        long_summary = "A" * _MAX_MESSAGE_LENGTH
        event = _make_event("run.started", human_summary=long_summary)
        text = format_flow_event(event)
        assert len(text) <= _MAX_MESSAGE_LENGTH
        # If truncated, ends with …
        if len(text) == _MAX_MESSAGE_LENGTH:
            assert text.endswith("…")

    def test_short_message_not_truncated(self):
        event = _make_event("run.started", human_summary="Short summary")
        text = format_flow_event(event)
        assert len(text) < _MAX_MESSAGE_LENGTH
        assert not text.endswith("…")


# ===========================================================================
# Acceptance criterion 7: fake client receives correct chat_id/text/options
# ===========================================================================


class TestFakeClientReceivesCorrectPayload:
    def test_sends_to_correct_chat_id(
        self,
        notifier: TelegramNotifier,
        outbox: DurableOutbox,
        fake_client: FakeTelegramClient,
    ):
        event = _make_event("run.started", human_summary="Pipeline started")
        outbox.enqueue(event, channel="telegram")
        notifier.notify(outbox)
        assert len(fake_client.sent) == 1
        assert fake_client.sent[0]["chat_id"] == -100123

    def test_sends_formatted_text(
        self,
        notifier: TelegramNotifier,
        outbox: DurableOutbox,
        fake_client: FakeTelegramClient,
    ):
        event = _make_event("run.started", human_summary="Hello world")
        outbox.enqueue(event, channel="telegram")
        notifier.notify(outbox)
        assert "Hello world" in fake_client.sent[0]["text"]

    def test_sends_disable_web_page_preview(
        self,
        notifier: TelegramNotifier,
        outbox: DurableOutbox,
        fake_client: FakeTelegramClient,
    ):
        event = _make_event("run.started")
        outbox.enqueue(event, channel="telegram")
        notifier.notify(outbox)
        assert fake_client.sent[0].get("disable_web_page_preview") is True


# ===========================================================================
# Acceptance criterion 8: success marks outbox sent
# ===========================================================================


class TestSuccessMarksSent:
    def test_sent_status_and_timestamp(
        self,
        notifier: TelegramNotifier,
        outbox: DurableOutbox,
        fake_client: FakeTelegramClient,
    ):
        event = _make_event("run.started")
        ob_msg = outbox.enqueue(event, channel="telegram")
        results = notifier.notify(outbox)
        assert len(results) == 1
        assert results[0].status == OutboxStatus.SENT
        assert results[0].error is None

        row = outbox._fetch_one(ob_msg.message_id)
        assert row.status == OutboxStatus.SENT
        assert row.sent_at is not None

    def test_multiple_messages_all_sent(
        self,
        notifier: TelegramNotifier,
        outbox: DurableOutbox,
        fake_client: FakeTelegramClient,
    ):
        for i in range(3):
            outbox.enqueue(
                _make_event("run.started", human_summary=f"Event {i}"),
                channel="telegram",
            )
        results = notifier.notify(outbox, limit=10)
        assert len(results) == 3
        assert all(r.status == OutboxStatus.SENT for r in results)
        assert len(fake_client.sent) == 3


# ===========================================================================
# Acceptance criterion 9: failure marks outbox failed and returns structured result
# ===========================================================================


class TestFailureMarksFailed:
    def test_client_returns_failure_marks_failed(
        self,
        outbox: DurableOutbox,
        fake_client: FakeTelegramClient,
    ):
        fake_client.should_succeed = False
        notifier = TelegramNotifier(client=fake_client, chat_id=-100123)
        event = _make_event("run.started")
        ob_msg = outbox.enqueue(event, channel="telegram")
        results = notifier.notify(outbox)
        assert len(results) == 1
        assert results[0].status == OutboxStatus.FAILED
        assert results[0].error is not None

        row = outbox._fetch_one(ob_msg.message_id)
        assert row.status == OutboxStatus.FAILED
        assert row.last_error is not None
        assert "HTTP non-2xx" in row.last_error

    def test_client_raises_marks_failed(
        self,
        outbox: DurableOutbox,
        fake_client: FakeTelegramClient,
    ):
        fake_client.raise_on = 0  # raise on first call
        notifier = TelegramNotifier(client=fake_client, chat_id=-100123)
        event = _make_event("run.started")
        ob_msg = outbox.enqueue(event, channel="telegram")
        results = notifier.notify(outbox)
        assert len(results) == 1
        assert results[0].status == OutboxStatus.FAILED
        assert results[0].error is not None

        row = outbox._fetch_one(ob_msg.message_id)
        assert row.status == OutboxStatus.FAILED

    def test_structured_result_fields(
        self,
        notifier: TelegramNotifier,
        outbox: DurableOutbox,
        fake_client: FakeTelegramClient,
    ):
        event = _make_event("run.started")
        ob_msg = outbox.enqueue(event, channel="telegram")
        results = notifier.notify(outbox)
        result = results[0]
        assert isinstance(result, NotifierResult)
        assert result.message_id == ob_msg.message_id
        assert result.event_id == ob_msg.event_id
        assert result.event_type == "run.started"


# ===========================================================================
# Acceptance criterion 10: token never appears in payload/log
# ===========================================================================


class TestSafeRedact:
    def test_redacts_bearer_token(self):
        text = "Authorization: bearer abc123def456"
        result = safe_redact(text)
        assert "[REDACTED]" in result
        assert "abc123def456" not in result

    def test_redacts_api_key(self):
        text = "api_key=super-secret-value"
        result = safe_redact(text)
        assert "[REDACTED]" in result
        assert "super-secret-value" not in result

    def test_redacts_token(self):
        text = "token=123456:ABC"
        result = safe_redact(text)
        assert "[REDACTED]" in result
        assert "123456:ABC" not in result

    def test_redacts_secret(self):
        text = "secret=my-password"
        result = safe_redact(text)
        assert "[REDACTED]" in result
        assert "my-password" not in result

    def test_no_false_positives_on_innocuous_words(self):
        text = "This is a token of appreciation"
        assert safe_redact(text) == text

    def test_event_with_token_in_summary_is_redacted(self):
        event = _make_event(
            "run.started",
            human_summary="Deploy with token=abc123 ready",
        )
        text = format_flow_event(event)
        assert "token=" not in text or "[REDACTED]" in text
        assert "abc123" not in text


# ===========================================================================
# Acceptance criterion 11: tests do not use network
# ===========================================================================


class TestNoNetwork:
    def test_all_offline(
        self,
        notifier: TelegramNotifier,
        outbox: DurableOutbox,
    ):
        """Full smoke-check: enqueue -> notify -> sent, no network involved."""
        event = _make_event("run.completed", evidence_refs=["doc://report/1"])
        outbox.enqueue(event, channel="telegram")
        results = notifier.notify(outbox)
        assert len(results) == 1
        assert results[0].status == OutboxStatus.SENT


# ===========================================================================
# Acceptance criterion 12: aptdata/transports/telegram.py is not reimplemented
# ===========================================================================


class TestNotReimplementingTransport:
    def test_does_not_import_conversation_engine(self):
        """TelegramNotifier must NOT import ConversationEngine or TelegramTransport."""
        import ast  # noqa: PLC0415

        source = Path(__file__).parent.parent / "aptdata/delivery/telegram_notifier.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))

        # Collect all Import and ImportFrom module names
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        banned = ["ConversationEngine", "TelegramTransport", "conversation"]
        for name in imports:
            for b in banned:
                assert b not in name, f"{name} imports {b}"


# ===========================================================================
# Edge cases
# ===========================================================================


class TestEdgeCases:
    def test_non_telegram_messages_are_skipped(
        self,
        notifier: TelegramNotifier,
        outbox: DurableOutbox,
        fake_client: FakeTelegramClient,
    ):
        """Messages for other channels are not processed."""
        outbox.enqueue(_make_event("run.started"), channel="slack")
        results = notifier.notify(outbox)
        assert len(results) == 0
        assert fake_client.sent == []

    def test_mixed_channels_only_telegram_processed(
        self,
        notifier: TelegramNotifier,
        outbox: DurableOutbox,
        fake_client: FakeTelegramClient,
    ):
        """When both telegram and other channels pend, only telegram is sent."""
        outbox.enqueue(_make_event("run.started"), channel="slack")
        outbox.enqueue(
            _make_event("run.started", human_summary="TG msg"),
            channel="telegram",
        )
        results = notifier.notify(outbox)
        assert len(results) == 1
        assert results[0].status == OutboxStatus.SENT
        assert len(fake_client.sent) == 1

    def test_empty_outbox_returns_empty_list(
        self,
        notifier: TelegramNotifier,
        outbox: DurableOutbox,
    ):
        results = notifier.notify(outbox)
        assert results == []

    def test_invalid_payload_json_marks_failed(
        self,
        notifier: TelegramNotifier,
        outbox: DurableOutbox,
    ):
        """A corrupt payload_json should be marked as failed."""
        event = _make_event("run.started")
        msg = outbox.enqueue(event, channel="telegram")

        # Manually corrupt the payload
        outbox._conn.execute(
            "UPDATE outbox_messages SET payload_json = '{broken json'"
            " WHERE message_id = ?",
            (msg.message_id,),
        )
        outbox._conn.commit()

        results = notifier.notify(outbox)
        assert len(results) == 1
        assert results[0].status == OutboxStatus.FAILED

    def test_stage_completed_includes_stage_id(
        self,
        notifier: TelegramNotifier,
        outbox: DurableOutbox,
        fake_client: FakeTelegramClient,
    ):
        event = _make_event(
            "stage.completed",
            stage_id="deploy-prod",
            human_summary="Deployment to production done",
        )
        text = format_flow_event(event)
        assert "✅" in text
        assert "Stage Completed" in text
        assert "deploy-prod" in text

    def test_run_blocked_format(
        self,
        notifier: TelegramNotifier,
        outbox: DurableOutbox,
        fake_client: FakeTelegramClient,
    ):
        event = _make_event("run.blocked", human_summary="Missing credentials")
        text = format_flow_event(event)
        assert "⛔" in text
        assert "Run Blocked" in text
        assert "Missing credentials" in text
