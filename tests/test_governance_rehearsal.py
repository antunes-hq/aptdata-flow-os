"""End-to-end read-only rehearsal tests."""

from aptdata.governance.rehearsal import run_read_only_rehearsal


def test_read_only_rehearsal_persists_and_recovers(tmp_path) -> None:
    result = run_read_only_rehearsal(tmp_path / "rehearsal.db")

    assert result["state"] == "integrated"
    assert result["ready_gate"] is True
    assert result["judge_verdict"] == "go"
    assert result["judge_independent"] is True
    assert result["maestro_action"] == "approve"
    assert result["integration_gate"] is True
    assert result["persisted_records"] == 15
    assert result["recovered_records_for_packet"] == 13
    assert result["transition_history"] == [
        "proposed",
        "ready",
        "running",
        "judging",
        "approved",
        "integrated",
    ]
    assert "produção" in result["scope_out"]


def test_rehearsal_is_explicitly_read_only(tmp_path) -> None:
    result = run_read_only_rehearsal(tmp_path / "rehearsal.db")

    assert "LLM" in result["scope_out"]
    assert "deploy" in result["scope_out"]
    assert result["work_packet_id"] == "wp_rehearsal_001"
