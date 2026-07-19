"""Tests for ``aptdata.agents.modes`` — ExecutionMode enum (ADR-002 §2.3).

O ``ExecutionMode`` é o eixo canônico de "como o aptdata executa", exposto
no CLI (``--mode``), no ``.aptdata/agents.yaml`` (``default_mode:``) e no
campo ``mode`` de toda saída ``--json`` de um comando de execução.
"""

from __future__ import annotations

import pytest

from aptdata.agents.modes import (
    MODE_DOCS,
    ExecutionMode,
    ModeDoc,
    mode_for_command,
    resolve_mode,
)


class TestExecutionModeEnum:
    def test_has_four_members(self):
        assert {m.value for m in ExecutionMode} == {
            "oneshot",
            "converse",
            "project",
            "orchestrated",
        }

    def test_is_str_enum(self):
        # str(ExecutionMode.X) == "X" (não "ExecutionMode.X") — assim json.dumps
        # e o typer usam o valor canônico.
        assert str(ExecutionMode.ONESHOT) == "oneshot"
        assert ExecutionMode.PROJECT == "project"
        # E compare com strings brutas como pede o contrato JSON.
        assert ExecutionMode.CONVERSE == "converse"
        assert ExecutionMode.ORCHESTRATED == "orchestrated"

    def test_from_str_canonical_value(self):
        assert ExecutionMode.from_str("oneshot") is ExecutionMode.ONESHOT
        assert ExecutionMode.from_str("converse") is ExecutionMode.CONVERSE
        assert ExecutionMode.from_str("project") is ExecutionMode.PROJECT
        assert ExecutionMode.from_str("orchestrated") is ExecutionMode.ORCHESTRATED

    def test_from_str_member_name_is_tolerant(self):
        """Aceita tanto o valor canônico quanto o nome do membro, case-insensitive."""
        assert ExecutionMode.from_str("ONESHOT") is ExecutionMode.ONESHOT
        assert ExecutionMode.from_str("OneShot") is ExecutionMode.ONESHOT

    def test_from_str_passthrough_enum(self):
        """Passar um ExecutionMode de volta é idempotente."""
        assert ExecutionMode.from_str(ExecutionMode.PROJECT) is ExecutionMode.PROJECT

    def test_from_str_rejects_unknown(self):
        with pytest.raises(ValueError, match="Unknown execution mode"):
            ExecutionMode.from_str("bogus")
        with pytest.raises(ValueError, match="Unknown execution mode"):
            ExecutionMode.from_str("")

    def test_each_member_has_docstring(self):
        """ADR-002 §2.3: cada modo é documentado — docstring não pode ser vazia."""
        for member in ExecutionMode:
            assert member.__doc__, f"{member.name} sem docstring"


class TestModeDocs:
    def test_one_doc_per_mode(self):
        modes_in_docs = {doc.mode for doc in MODE_DOCS}
        assert modes_in_docs == set(ExecutionMode)

    def test_doc_has_short_description_and_cli_command(self):
        for doc in MODE_DOCS:
            assert isinstance(doc, ModeDoc)
            assert doc.short, f"{doc.mode.value} sem short"
            assert doc.description, f"{doc.mode.value} sem description"
            assert doc.cli_command.startswith(
                "aptdata "
            ), f"{doc.mode.value} cli_command não começa com 'aptdata '"


class TestCommandDefaults:
    @pytest.mark.parametrize(
        "group,command,expected",
        [
            ("agents", "send", ExecutionMode.ONESHOT),
            ("agents", "dispatch", ExecutionMode.ORCHESTRATED),
            ("agents", "route", ExecutionMode.ORCHESTRATED),
            ("converse", "", ExecutionMode.CONVERSE),
            ("project", "run", ExecutionMode.PROJECT),
            ("project", "plan", ExecutionMode.PROJECT),
        ],
    )
    def test_natural_default(self, group, command, expected):
        assert mode_for_command(group, command) is expected

    def test_unknown_command_returns_none(self):
        assert mode_for_command("agents", "bogus") is None
        assert mode_for_command("bogus", "") is None


class TestResolveMode:
    def test_explicit_string_wins(self):
        assert (
            resolve_mode("orchestrated", "agents", "send") is ExecutionMode.ORCHESTRATED
        )

    def test_explicit_enum_wins(self):
        assert (
            resolve_mode(ExecutionMode.PROJECT, "agents", "send")
            is ExecutionMode.PROJECT
        )

    def test_project_default_beats_command_default(self):
        # default_mode do projeto vence o default natural do comando.
        assert (
            resolve_mode(None, "agents", "send", project_default=ExecutionMode.CONVERSE)
            is ExecutionMode.CONVERSE
        )

    def test_command_default_when_no_explicit_and_no_project(self):
        assert resolve_mode(None, "agents", "send") is ExecutionMode.ONESHOT
        assert resolve_mode(None, "converse", "") is ExecutionMode.CONVERSE
        assert resolve_mode(None, "project", "run") is ExecutionMode.PROJECT
        assert resolve_mode(None, "agents", "dispatch") is ExecutionMode.ORCHESTRATED

    def test_falls_back_to_oneshot_for_unknown_command(self):
        """Nunca retorna None — último fallback é oneshot."""
        assert resolve_mode(None, "bogus", "cmd") is ExecutionMode.ONESHOT

    def test_invalid_explicit_raises(self):
        with pytest.raises(ValueError, match="Unknown execution mode"):
            resolve_mode("bogus", "agents", "send")
