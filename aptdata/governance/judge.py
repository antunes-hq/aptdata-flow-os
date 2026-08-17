"""Deterministic read-only Judge for trusted squad packets."""

from __future__ import annotations

from datetime import datetime, timezone

from aptdata.governance.models import (
    EvidenceRecord,
    EvidenceResult,
    Finding,
    IndependenceCheck,
    JudgeCheck,
    JudgeResult,
    SquadDefinition,
    Verdict,
    WorkPacket,
)


class GovernanceJudge:
    """Audit a packet and its evidence without executing or mutating anything."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id

    def judge(
        self,
        packet: WorkPacket,
        squad: SquadDefinition,
        evidence: list[EvidenceRecord],
        *,
        created_at: datetime | None = None,
    ) -> JudgeResult:
        """Return a deterministic verdict from the supplied records."""
        created_at = created_at or datetime.now(timezone.utc)
        findings: list[Finding] = []
        checks: list[JudgeCheck] = []

        required_roles = {role.id for role in squad.roles if role.required}
        assignments = {item.role: item.agent_id for item in packet.assignments}
        missing_roles = sorted(required_roles - assignments.keys())
        checks.append(
            JudgeCheck(
                id="J-ASSIGNMENTS",
                subject="required_assignments",
                result=(EvidenceResult.FAIL if missing_roles else EvidenceResult.PASS),
                note=(
                    f"missing roles: {missing_roles}"
                    if missing_roles
                    else "all required roles assigned"
                ),
            )
        )
        if missing_roles:
            findings.append(
                Finding(
                    severity="high",
                    kind="scope",
                    statement=f"Missing required assignments: {missing_roles}",
                    required_action="assign every required role",
                )
            )

        executor_id = assignments.get("executor")
        judge_assignment_id = assignments.get("judge")
        independent = bool(
            executor_id
            and judge_assignment_id
            and executor_id != judge_assignment_id
        )
        independence_reason = (
            "executor and judge are distinct assignments"
            if independent
            else "executor and judge are missing or assigned to the same agent"
        )
        checks.append(
            JudgeCheck(
                id="J-INDEPENDENCE",
                subject="judge_independence",
                result=(EvidenceResult.PASS if independent else EvidenceResult.FAIL),
                note=independence_reason,
            )
        )
        if not independent:
            findings.append(
                Finding(
                    severity="critical",
                    kind="security",
                    statement="Judge is not independent from the executor",
                    required_action="assign a distinct Judge agent",
                )
            )

        evidence_refs = [item.id for item in evidence]
        if not evidence:
            evidence_result = EvidenceResult.FAIL
            evidence_note = "no evidence records supplied"
            findings.append(
                Finding(
                    severity="critical",
                    kind="missing_evidence",
                    statement="No evidence records supplied",
                    required_action="attach verifiable evidence",
                )
            )
        elif any(item.result is EvidenceResult.FAIL for item in evidence):
            evidence_result = EvidenceResult.FAIL
            evidence_note = "at least one evidence record failed"
            findings.append(
                Finding(
                    severity="critical",
                    kind="regression",
                    statement="At least one evidence record failed",
                    evidence_refs=evidence_refs,
                    required_action="resolve failed evidence before integration",
                )
            )
        elif any(item.result is EvidenceResult.INCONCLUSIVE for item in evidence):
            evidence_result = EvidenceResult.INCONCLUSIVE
            evidence_note = "at least one evidence record is inconclusive"
            findings.append(
                Finding(
                    severity="high",
                    kind="missing_evidence",
                    statement="Evidence is inconclusive",
                    evidence_refs=evidence_refs,
                    required_action=(
                        "replace inconclusive evidence with a reproducible check"
                    ),
                )
            )
        else:
            evidence_result = EvidenceResult.PASS
            evidence_note = "all supplied evidence passed"
        checks.append(
            JudgeCheck(
                id="J-EVIDENCE",
                subject="evidence",
                result=evidence_result,
                evidence_refs=evidence_refs,
                note=evidence_note,
            )
        )

        if findings:
            verdict = (
                Verdict.INCONCLUSIVE
                if evidence_result is EvidenceResult.INCONCLUSIVE and all(
                    finding.severity != "critical" for finding in findings
                )
                else Verdict.NO_GO
            )
        else:
            verdict = Verdict.GO

        return JudgeResult(
            id=f"jr_{packet.id}_{self.agent_id}",
            work_packet_id=packet.id,
            judge_agent_id=self.agent_id,
            independence_check=IndependenceCheck(
                executor_agent_id=executor_id or "missing",
                independent=independent,
                reason=independence_reason,
            ),
            checks=checks,
            findings=findings,
            verdict=verdict,
            created_at=created_at,
        )


__all__ = ["GovernanceJudge"]
