"""FlowEvent — a versioned, immutable event envelope for durable delivery.

Why this exists:
- Separates the canonical event payload from its delivery state.
- Every event carries its own schema version so consumers can safely
  evolve their understanding without breaking on old events.
- All required fields allow tracing an event back to its originating
  workspace, project, and run — crucial for observability and audit.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FlowEvent(BaseModel):
    """A versioned, immutable event envelope for the Flow OS.

    FlowEvents are the canonical payload that gets placed into the
    durable outbox for delivery to channels such as Telegram or a
    browser grant. Once published, an event is never mutated.

    Required fields trace the event to its origin (workspace/project/
    run) and carry a human-readable summary. Optional fields carry
    workflow-specific context (definition, stage, next action) and
    supporting evidence references.
    """

    model_config = ConfigDict(
        frozen=True,  # events are immutable once created
        extra="forbid",  # no unexpected fields in the envelope
        use_enum_values=False,
    )

    # -- Required fields ---------------------------------------------------
    event_id: UUID = Field(
        ...,
        description="Unique identifier, provided by producer or auto-generated.",
    )
    schema_version: int = Field(
        ...,
        description="Schema version number for forward/backward compatibility.",
    )
    event_type: str = Field(
        ...,
        description="Machine-readable event type (e.g. 'pipeline.completed').",
    )
    workspace_id: str = Field(
        ..., description="The workspace this event originated from."
    )
    project_id: str = Field(
        ..., description="The project within the workspace."
    )
    run_id: str = Field(
        ..., description="The execution run that produced this event."
    )
    severity: str = Field(
        ...,
        description="Severity level (e.g. info, warning, error, critical).",
    )
    human_summary: str = Field(
        ...,
        description="Human-readable one-line summary of what happened.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the event was created (UTC, timezone-aware).",
    )

    # -- Optional fields ---------------------------------------------------
    flow_definition_id: str | None = Field(
        default=None,
        description=(
            "Optional: reference to the flow definition"
            " that produced this event."
        ),
    )
    stage_id: str | None = Field(
        default=None,
        description="Optional: specific stage within the flow.",
    )
    next_action: str | None = Field(
        default=None,
        description="Optional: suggested next action for a consumer.",
    )
    evidence_refs: list[str] | None = Field(
        default=None,
        description="Optional: references to supporting evidence documents.",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional: arbitrary JSON-serializable metadata.",
    )
