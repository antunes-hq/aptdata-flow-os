"""Trace identity tests for the integration gate."""

from aptdata.governance import check_integration
from tests.test_governance_gates import judge, maestro, packet


def test_integration_rejects_cross_packet_judge() -> None:
    work = packet()
    work.state = "approved"
    other = judge().model_copy(update={"work_packet_id": "wp_other"})
    report = check_integration(work, other, maestro())
    assert not report.passed
    assert "TRACE-001" in report.codes


def test_integration_rejects_cross_judge_maestro() -> None:
    work = packet()
    work.state = "approved"
    other = maestro().model_copy(update={"judge_result_id": "jr_other"})
    report = check_integration(work, judge(), other)
    assert not report.passed
    assert "TRACE-001" in report.codes


def test_integration_rejects_non_independent_judge_even_on_no_go() -> None:
    work = packet()
    work.state = "approved"
    rejected_payload = judge().model_dump(mode="json")
    rejected_payload["independence_check"] = {
        "executor_agent_id": "coder",
        "independent": False,
        "reason": "same agent",
    }
    rejected_payload["verdict"] = "no_go"
    rejected_payload["findings"] = [
        {
            "severity": "critical",
            "kind": "security",
            "statement": "same agent",
        }
    ]
    rejected = type(judge()).model_validate(rejected_payload)
    report = check_integration(work, rejected, maestro())
    assert not report.passed
    assert "JUDGE-001" in report.codes


def test_integration_accepts_matching_identities() -> None:
    work = packet()
    work.state = "approved"
    report = check_integration(work, judge(), maestro())
    assert report.passed


def test_model_copy_nested_update_is_not_used_by_gate_contract() -> None:
    """The gate reads typed nested data; callers must revalidate external payloads."""
    work = packet()
    work.state = "approved"
    unsafe = judge().model_copy(
        update={
            "independence_check": {
                "executor_agent_id": "coder",
                "independent": False,
                "reason": "unvalidated nested payload",
            }
        }
    )
    assert isinstance(unsafe.independence_check, dict)
    assert check_integration(work, unsafe, maestro()).passed is False
