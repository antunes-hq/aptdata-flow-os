"""Pure confidence gates for trusted squad governance."""

from __future__ import annotations

from dataclasses import dataclass, field

from aptdata.governance.models import (
    EvidenceRecord,
    EvidenceResult,
    JudgeResult,
    MaestroAction,
    MaestroDecision,
    PacketState,
    SquadDefinition,
    WorkPacket,
)


@dataclass(frozen=True)
class GateFinding:
    code: str
    message: str


@dataclass
class GateReport:
    """Machine-readable gate result with compact findings."""

    passed: bool
    findings: list[GateFinding] = field(default_factory=list)

    @property
    def codes(self) -> list[str]:
        return [finding.code for finding in self.findings]


def check_ready_for_judging(
    packet: WorkPacket,
    squad: SquadDefinition,
    evidence: list[EvidenceRecord],
) -> GateReport:
    """Check whether a running packet has enough material for the Judge."""
    findings: list[GateFinding] = []
    required_roles = {role.id for role in squad.roles if role.required}
    assigned_roles = {assignment.role for assignment in packet.assignments}
    missing_roles = sorted(required_roles - assigned_roles)
    if missing_roles:
        findings.append(
            GateFinding("SQUAD-001", f"missing required assignments: {missing_roles}")
        )

    if not evidence:
        findings.append(GateFinding("EVID-005", "no evidence records attached"))
    if any(item.result is EvidenceResult.INCONCLUSIVE for item in evidence):
        findings.append(
            GateFinding("EVID-002", "inconclusive evidence cannot close gate")
        )

    if packet.state not in {PacketState.RUNNING, PacketState.JUDGING}:
        findings.append(
            GateFinding("PACKET-002", f"packet state is not runnable: {packet.state}")
        )

    return GateReport(not findings, findings)


def check_integration(
    packet: WorkPacket,
    judge: JudgeResult,
    maestro: MaestroDecision | None,
) -> GateReport:
    """Check whether a judged packet may become integrated."""
    findings: list[GateFinding] = []
    if packet.state is not PacketState.APPROVED:
        findings.append(
            GateFinding("PACKET-002", "packet must be approved before integration")
        )
    if judge.verdict not in {"go", "go_with_conditions"}:
        findings.append(
            GateFinding(
                "JUDGE-002",
                f"judge verdict does not permit integration: {judge.verdict}",
            )
        )
    if maestro is None:
        findings.append(GateFinding("MAESTRO-001", "MaestroDecision is required"))
    elif maestro.action not in {
        MaestroAction.APPROVE,
        MaestroAction.APPROVE_WITH_CONDITIONS,
    }:
        findings.append(
            GateFinding(
                "MAESTRO-001",
                f"Maestro action does not approve: {maestro.action}",
            )
        )
    return GateReport(not findings, findings)


__all__ = ["GateFinding", "GateReport", "check_integration", "check_ready_for_judging"]
