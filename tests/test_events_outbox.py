"""Contract tests for F1.2a — FlowEvent envelope + DurableOutbox.

Each test maps to one acceptance criterion from the workpacket.
All tests are offline/deterministic — no network, no tokens.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from aptdata.delivery.outbox import DurableOutbox, OutboxStatus
from aptdata.events.models import FlowEvent

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def event() -> FlowEvent:
    """A fully populated valid FlowEvent for round-trip tests."""
    return FlowEvent(
        event_id=uuid4(),
        schema_version=1,
        event_type="pipeline.completed",
        workspace_id="ws-main",
        project_id="proj-alpha",
        run_id="run-42",
        severity="info",
        human_summary="Pipeline completed successfully",
        created_at=datetime.now(timezone.utc),
        flow_definition_id="flow-def-001",
        stage_id="stage-3",
        next_action="notify_telegram",
        evidence_refs=["doc://evidence/001", "doc://evidence/002"],
        metadata={"duration_ms": 1234, "record_count": 500},
    )


@pytest.fixture()
def ob(tmp_path: Path) -> DurableOutbox:
    """A DurableOutbox backed by a temporary SQLite database."""
    return DurableOutbox(db_path=str(tmp_path / "outbox_test.db"))


# ===========================================================================
# Acceptance criterion 1: valid event round-trips JSON without losing fields
# ===========================================================================


class TestFlowEventRoundTrip:
    def test_all_fields_survive_roundtrip(self, event: FlowEvent):
        """Criterion 1: every field survives serialize → deserialize."""
        raw = event.model_dump_json()
        restored = FlowEvent.model_validate_json(raw)

        assert restored.event_id == event.event_id
        assert restored.schema_version == event.schema_version
        assert restored.event_type == event.event_type
        assert restored.workspace_id == event.workspace_id
        assert restored.project_id == event.project_id
        assert restored.run_id == event.run_id
        assert restored.severity == event.severity
        assert restored.human_summary == event.human_summary
        assert restored.created_at == event.created_at
        assert restored.flow_definition_id == event.flow_definition_id
        assert restored.stage_id == event.stage_id
        assert restored.next_action == event.next_action
        assert restored.evidence_refs == event.evidence_refs
        assert restored.metadata == event.metadata

    def test_json_output_is_valid_json(self, event: FlowEvent):
        """The serialized form is parseable as plain JSON."""
        raw = event.model_dump_json()
        parsed = json.loads(raw)
        assert parsed["event_id"] == str(event.event_id)
        assert parsed["event_type"] == "pipeline.completed"
        assert parsed["schema_version"] == 1

    def test_created_at_is_tz_aware_utc(self, event: FlowEvent):
        """created_at must carry UTC timezone info."""
        assert event.created_at.tzinfo is not None
        assert event.created_at.utcoffset() is not None
        raw = event.model_dump_json()
        restored = FlowEvent.model_validate_json(raw)
        assert restored.created_at.tzinfo is not None


# ===========================================================================
# Acceptance criterion 2: invalid event fails with deterministic error
# ===========================================================================


class TestFlowEventValidation:
    def test_missing_required_field_raises(self):
        """Omission of a required field raises ValidationError."""
        with pytest.raises(Exception) as exc:
            FlowEvent(
                event_id=uuid4(),
                schema_version=1,
                event_type="test",
                # missing workspace_id
                project_id="p",
                run_id="r",
                severity="info",
                human_summary="s",
                created_at=datetime.now(timezone.utc),
            )
        err = str(exc.value)
        assert "workspace_id" in err or "field required" in err

    def test_any_severity_accepted(self):
        """Severity is a string — any value is valid per contract."""
        ev = FlowEvent(
            event_id=uuid4(),
            schema_version=1,
            event_type="test",
            workspace_id="ws",
            project_id="p",
            run_id="r",
            severity="custom-level",
            human_summary="s",
            created_at=datetime.now(timezone.utc),
        )
        assert ev.severity == "custom-level"

    def test_empty_event_id_fails(self):
        """An empty string for event_id should raise (UUID required)."""
        with pytest.raises(Exception):
            FlowEvent(
                event_id="",
                schema_version=1,
                event_type="test",
                workspace_id="ws",
                project_id="p",
                run_id="r",
                severity="info",
                human_summary="s",
                created_at=datetime.now(timezone.utc),
            )


# ===========================================================================
# Acceptance criterion 3: enqueue creates a pending message
# ===========================================================================


class TestOutboxEnqueue:
    def test_enqueue_creates_pending(self, event: FlowEvent, ob: DurableOutbox):
        """Calling enqueue results in one pending row."""
        msg = ob.enqueue(event, channel="telegram")
        assert msg.status == OutboxStatus.PENDING
        assert msg.attempts == 0
        assert msg.event_id == str(event.event_id)
        assert msg.channel == "telegram"
        assert msg.sent_at is None
        assert msg.last_error is None

        claimed = ob.claim_pending(limit=10)
        assert len(claimed) == 1
        assert claimed[0].message_id == msg.message_id

    def test_enqueue_persists_payload(self, event: FlowEvent, ob: DurableOutbox):
        """The payload_json field contains a valid serialized FlowEvent."""
        msg = ob.enqueue(event, channel="slack")
        payload = json.loads(msg.payload_json)
        assert payload["event_id"] == str(event.event_id)
        assert payload["event_type"] == event.event_type


# ===========================================================================
# Acceptance criterion 4: duplicate enqueue does not duplicate
# ===========================================================================


class TestOutboxDeduplication:
    def test_same_event_same_channel_dedup(
        self, event: FlowEvent, ob: DurableOutbox
    ):
        """Enqueuing same (event_id, channel) twice returns existing record."""
        msg1 = ob.enqueue(event, channel="telegram")
        msg2 = ob.enqueue(event, channel="telegram")
        assert msg1.message_id == msg2.message_id

        claimed = ob.claim_pending(limit=100)
        keys = [m.event_id + ":" + m.channel for m in claimed]
        assert keys.count(str(event.event_id) + ":telegram") == 1

    def test_same_event_diff_channels(
        self, event: FlowEvent, ob: DurableOutbox
    ):
        """Two channels for same event produce separate messages."""
        msg1 = ob.enqueue(event, channel="telegram")
        msg2 = ob.enqueue(event, channel="slack")
        assert msg1.message_id != msg2.message_id

        claimed = ob.claim_pending(limit=100)
        channels = {m.channel for m in claimed}
        assert "telegram" in channels
        assert "slack" in channels


# ===========================================================================
# Acceptance criteria 5 + 6 + 7: claim / mark_sent / mark_failed
# ===========================================================================


class TestOutboxClaimAndMark:
    def test_claim_bumps_attempts(self, event: FlowEvent, ob: DurableOutbox):
        """Criterion 5: claim picks up pending and increments attempts."""
        ob.enqueue(event, channel="email")
        claimed = ob.claim_pending(limit=10)
        assert len(claimed) == 1
        assert claimed[0].attempts == 1  # was 0, now 1 after claim

        # Still pending — claimable again with bumped attempts
        claimed2 = ob.claim_pending(limit=10)
        assert len(claimed2) == 1
        assert claimed2[0].attempts == 2

    def test_mark_sent_idempotent(self, event: FlowEvent, ob: DurableOutbox):
        """Criterion 6: mark_sent sets status=sent and records sent_at."""
        ob.enqueue(event, channel="webhook")
        claimed = ob.claim_pending(limit=10)
        msg_id = claimed[0].message_id

        ob.mark_sent(msg_id)
        row = ob._fetch_one(msg_id)
        assert row.status == OutboxStatus.SENT
        assert row.sent_at is not None

        # Idempotent: second call does not raise
        ob.mark_sent(msg_id)
        row2 = ob._fetch_one(msg_id)
        assert row2.status == OutboxStatus.SENT

    def test_mark_failed_records_error(
        self, event: FlowEvent, ob: DurableOutbox
    ):
        """Criterion 7: mark_failed stores a sanitized error string."""
        ob.enqueue(event, channel="http")
        claimed = ob.claim_pending(limit=10)
        msg_id = claimed[0].message_id

        ob.mark_failed(msg_id, "Connection refused: port 443")
        row = ob._fetch_one(msg_id)
        assert row.status == OutboxStatus.FAILED
        assert row.last_error == "Connection refused: port 443"

    def test_error_sanitized_no_tokens(
        self, event: FlowEvent, ob: DurableOutbox
    ):
        """Errors with tokens/secrets should be truncated to 512 chars."""
        ob.enqueue(event, channel="http")
        claimed = ob.claim_pending(limit=10)
        msg_id = claimed[0].message_id

        long_err = "x" * 1000 + "SECRET_TOKEN=abc123"
        ob.mark_failed(msg_id, long_err)
        row = ob._fetch_one(msg_id)
        assert row.last_error is not None
        assert len(row.last_error) <= 512


# ===========================================================================
# Acceptance criterion 8: sent message does not return to pending
# ===========================================================================


class TestOutboxNoRollback:
    def test_sent_not_claimable(self, event: FlowEvent, ob: DurableOutbox):
        """Once sent, a message is excluded from claim_pending."""
        ob.enqueue(event, channel="queue")
        claimed = ob.claim_pending(limit=10)
        msg_id = claimed[0].message_id
        ob.mark_sent(msg_id)

        claimed2 = ob.claim_pending(limit=10)
        sent_ids = [m.message_id for m in claimed2]
        assert msg_id not in sent_ids

    def test_failed_is_claimable_again(
        self, event: FlowEvent, ob: DurableOutbox
    ):
        """Failed messages can be reclaimed (retry semantics)."""
        ob.enqueue(event, channel="retry-channel")
        claimed = ob.claim_pending(limit=10)
        msg_id = claimed[0].message_id
        ob.mark_failed(msg_id, "temporary error")

        reclaimed = ob.claim_pending(limit=10)
        assert len(reclaimed) == 1
        assert reclaimed[0].attempts == 2  # was 1, now 2


# ===========================================================================
# Acceptance criterion 9: two channels for same event are independent
# ===========================================================================


class TestOutboxIndependentChannels:
    def test_channels_independent(self, event: FlowEvent, ob: DurableOutbox):
        """Sending one channel does not affect the other's pending status."""
        ob.enqueue(event, channel="telegram")
        ob.enqueue(event, channel="slack")

        all_pending = ob.claim_pending(limit=10)
        ids_by_ch = {m.channel: m.message_id for m in all_pending}

        ob.mark_sent(ids_by_ch["telegram"])

        remaining = ob.claim_pending(limit=10)
        assert len(remaining) == 1
        assert remaining[0].channel == "slack"

        tel = ob._fetch_one(ids_by_ch["telegram"])
        assert tel.status == OutboxStatus.SENT


# ===========================================================================
# Acceptance criterion 10: storage survives close/reopen
# ===========================================================================


class TestOutboxPersistence:
    def test_messages_survive_reopen(self, event: FlowEvent, tmp_path: Path):
        """Messages committed to SQLite survive after closing and reopening."""
        db = tmp_path / "survive.db"
        box1 = DurableOutbox(db_path=str(db))
        box1.enqueue(event, channel="persistent")
        box1.close()

        box2 = DurableOutbox(db_path=str(db))
        claimed = box2.claim_pending(limit=10)
        assert len(claimed) == 1
        assert claimed[0].event_id == str(event.event_id)
        box2.close()

    def test_sent_status_survives_reopen(
        self, event: FlowEvent, tmp_path: Path
    ):
        """A sent message stays sent after reconnect."""
        db = tmp_path / "status_survive.db"
        box1 = DurableOutbox(db_path=str(db))
        box1.enqueue(event, channel="survivor")
        claimed = box1.claim_pending(limit=10)
        box1.mark_sent(claimed[0].message_id)
        box1.close()

        box2 = DurableOutbox(db_path=str(db))
        row = box2._fetch_one(claimed[0].message_id)
        assert row.status == OutboxStatus.SENT
        box2.close()


# ===========================================================================
# Acceptance criterion 11: no network or tokens in tests
# ===========================================================================


class TestNoNetwork:
    def test_end_to_end_offline(self, event: FlowEvent, ob: DurableOutbox):
        """Smoke check — enqueue + claim works with no side effects."""
        ob.enqueue(event, channel="offline")
        claimed = ob.claim_pending(limit=5)
        assert len(claimed) == 1
        assert claimed[0].channel == "offline"
