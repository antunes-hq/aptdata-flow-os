"""Typed v0.1 contracts for trusted squad governance.

These models validate the contract only. Persistence, dispatch and autonomous
execution are deliberately out of scope for this first slice.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Domain(StrEnum):
    PERSONAL = "personal"
    LEARNING = "learning"
    CREATIVE = "creative"
    DEVELOPMENT = "development"
    OTHER = "other"


class PacketState(StrEnum):
    PROPOSED = "proposed"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    AWAITING_MAESTRO = "awaiting_maestro"
    JUDGING = "judging"
    APPROVED = "approved"
    REJECTED = "rejected"
    INTEGRATED = "integrated"
    CANCELLED = "cancelled"


class EvidenceKind(StrEnum):
    TEST = "test"
    LINT = "lint"
    BUILD = "build"
    RUNTIME = "runtime"
    REVIEW = "review"
    FILE = "file"
    COMMIT = "commit"
    DEPLOY = "deploy"
    DECISION = "decision"


class EvidenceResult(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


class Verdict(StrEnum):
    GO = "go"
    GO_WITH_CONDITIONS = "go_with_conditions"
    NO_GO = "no_go"
    INCONCLUSIVE = "inconclusive"


class MaestroAction(StrEnum):
    APPROVE = "approve"
    APPROVE_WITH_CONDITIONS = "approve_with_conditions"
    REJECT = "reject"
    REQUEST_REVISION = "request_revision"
    PAUSE = "pause"


class ContractModel(BaseModel):
    """Strict JSON contract base: no silent fields or coercion surprises."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


def _nonempty(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be empty")
    return value


class SourceRef(ContractModel):
    actor: str
    channel: str
    reference: str

    _actor = _nonempty
    _channel = _nonempty
    _reference = _nonempty


class ContextPacket(ContractModel):
    id: str
    version: int = Field(default=1, ge=1)
    source: SourceRef
    intent: str
    why: str
    domain: Domain
    desired_experience: str = ""
    constraints: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    maestro_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_context(self) -> ContextPacket:
        for field_name in ("id", "intent", "why"):
            _nonempty(getattr(self, field_name))
        return self


class SquadRole(ContractModel):
    id: str
    capability: str
    required: bool = True


class ExecutorPolicy(ContractModel):
    allowed: list[str] = Field(min_length=1)
    fallback: str = "explicit_only"


class IndependencePolicy(ContractModel):
    judge_must_differ_from_executor: bool = True
    judge_must_receive_evidence: bool = True
    maestro_approval_required_for_high_impact: bool = True


class SquadDefinition(ContractModel):
    id: str
    version: int = Field(default=1, ge=1)
    name: str
    roles: list[SquadRole] = Field(min_length=1)
    executor_policy: ExecutorPolicy
    independence: IndependencePolicy = Field(default_factory=IndependencePolicy)
    output_contract: str = "workpacket_v1"

    @model_validator(mode="after")
    def validate_roles(self) -> SquadDefinition:
        ids = [role.id for role in self.roles]
        if len(ids) != len(set(ids)):
            raise ValueError("squad role ids must be unique")
        if not any(role.id == "judge" and role.required for role in self.roles):
            raise ValueError("a required judge role is mandatory")
        return self


class AcceptanceCriterion(ContractModel):
    id: str
    description: str
    verification: str


class Risk(ContractModel):
    level: str
    hazards: list[str] = Field(default_factory=list)
    rollback: str


class Assignment(ContractModel):
    role: str
    agent_id: str
    accepted_at: datetime


class Decision(ContractModel):
    id: str
    question: str
    options: list[str] = Field(default_factory=list)
    selected: str | None = None
    authority: str
    evidence_refs: list[str] = Field(default_factory=list)


_ALLOWED_TRANSITIONS: dict[PacketState, frozenset[PacketState]] = {
    PacketState.PROPOSED: frozenset(
        {PacketState.READY, PacketState.CANCELLED}
    ),
    PacketState.READY: frozenset(
        {PacketState.RUNNING, PacketState.BLOCKED, PacketState.CANCELLED}
    ),
    PacketState.RUNNING: frozenset(
        {
            PacketState.AWAITING_MAESTRO,
            PacketState.JUDGING,
            PacketState.BLOCKED,
            PacketState.CANCELLED,
        }
    ),
    PacketState.AWAITING_MAESTRO: frozenset(
        {PacketState.RUNNING, PacketState.CANCELLED}
    ),
    PacketState.JUDGING: frozenset(
        {PacketState.APPROVED, PacketState.REJECTED, PacketState.BLOCKED}
    ),
    PacketState.APPROVED: frozenset({PacketState.INTEGRATED}),
    PacketState.REJECTED: frozenset(
        {PacketState.PROPOSED, PacketState.CANCELLED}
    ),
    PacketState.BLOCKED: frozenset({PacketState.READY, PacketState.CANCELLED}),
    PacketState.INTEGRATED: frozenset(),
    PacketState.CANCELLED: frozenset(),
}


class WorkPacket(ContractModel):
    id: str
    version: int = Field(default=1, ge=1)
    context_packet_id: str
    squad_definition_id: str
    objective: str
    scope_in: list[str] = Field(default_factory=list, alias="scope_in")
    scope_out: list[str] = Field(default_factory=list, alias="scope_out")
    acceptance_criteria: list[AcceptanceCriterion] = Field(min_length=1)
    constraints: list[str] = Field(default_factory=list)
    files_or_surfaces: list[str] = Field(default_factory=list)
    risk: Risk
    assignments: list[Assignment] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    state: PacketState = PacketState.PROPOSED
    evidence_refs: list[str] = Field(default_factory=list)

    model_config = ConfigDict(
        extra="forbid", validate_assignment=True, populate_by_name=True
    )

    def can_transition(self, target: PacketState) -> bool:
        return target in _ALLOWED_TRANSITIONS[self.state]

    def transition(self, target: PacketState) -> WorkPacket:
        if not self.can_transition(target):
            raise ValueError(f"invalid WorkPacket transition: {self.state} -> {target}")
        self.state = target
        return self

    @model_validator(mode="after")
    def validate_assignments(self) -> WorkPacket:
        roles = [assignment.role for assignment in self.assignments]
        if len(roles) != len(set(roles)):
            raise ValueError("WorkPacket assignments must have unique roles")
        for field_name in (
            "id",
            "context_packet_id",
            "squad_definition_id",
            "objective",
        ):
            _nonempty(getattr(self, field_name))
        return self


class EvidenceSource(ContractModel):
    path: str
    revision: str


class EvidenceRecord(ContractModel):
    id: str
    version: int = Field(default=1, ge=1)
    work_packet_id: str
    kind: EvidenceKind
    claim: str
    command: str | None = None
    output_digest: str | None = None
    result: EvidenceResult
    source: EvidenceSource
    captured_at: datetime
    captured_by: str
    limitations: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_evidence(self) -> EvidenceRecord:
        if self.result != EvidenceResult.INCONCLUSIVE and not self.output_digest:
            raise ValueError("pass/fail evidence requires output_digest")
        for field_name in ("id", "work_packet_id", "claim", "captured_by"):
            _nonempty(getattr(self, field_name))
        return self


class IndependenceCheck(ContractModel):
    executor_agent_id: str
    independent: bool
    reason: str


class JudgeCheck(ContractModel):
    id: str
    subject: str
    result: EvidenceResult
    evidence_refs: list[str] = Field(default_factory=list)
    note: str = ""


class Finding(ContractModel):
    severity: str
    kind: str
    statement: str
    evidence_refs: list[str] = Field(default_factory=list)
    required_action: str | None = None


class JudgeResult(ContractModel):
    id: str
    version: int = Field(default=1, ge=1)
    work_packet_id: str
    judge_agent_id: str
    independence_check: IndependenceCheck
    checks: list[JudgeCheck] = Field(min_length=1)
    findings: list[Finding] = Field(default_factory=list)
    verdict: Verdict
    conditions: list[str] = Field(default_factory=list)
    residual_risks: list[str] = Field(default_factory=list)
    created_at: datetime

    @model_validator(mode="after")
    def validate_verdict(self) -> JudgeResult:
        if (
            not self.independence_check.independent
            and self.verdict is not Verdict.NO_GO
        ):
            raise ValueError("non-independent JudgeResult must be no_go")
        if self.verdict == Verdict.GO_WITH_CONDITIONS and not self.conditions:
            raise ValueError("go_with_conditions requires conditions")
        if self.verdict == Verdict.NO_GO and not self.findings:
            raise ValueError("no_go requires findings")
        return self


class MaestroDecision(ContractModel):
    id: str
    work_packet_id: str
    judge_result_id: str
    action: MaestroAction
    rationale: str
    accepted_risks: list[str] = Field(default_factory=list)
    rejected_risks: list[str] = Field(default_factory=list)
    scope_change: str | None = None
    actor: str
    created_at: datetime


__all__ = [
    "AcceptanceCriterion", "Assignment", "ContextPacket", "Decision", "Domain",
    "EvidenceKind", "EvidenceRecord", "EvidenceResult", "EvidenceSource", "Finding",
    "IndependenceCheck",
    "JudgeCheck",
    "JudgeResult",
    "MaestroAction",
    "MaestroDecision",
    "PacketState",
    "Risk",
    "SquadDefinition",
    "SquadRole",
    "SourceRef",
    "Verdict",
    "WorkPacket",
]


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for contract fixtures."""
    return datetime.now(timezone.utc)
