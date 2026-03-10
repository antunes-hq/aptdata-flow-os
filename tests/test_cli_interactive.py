"""Tests for aptdata.cli.interactive — wizard flows with mocked prompts."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

from typer.testing import CliRunner

from aptdata.cli import interactive as interactive_module

runner = CliRunner()


# ---------------------------------------------------------------------------
# _select, _text, _confirm helpers (without questionary)
# ---------------------------------------------------------------------------


class TestHelperFallbacks:
    def test_select_fallback(self, monkeypatch):
        """_select falls back to typer.prompt when questionary is unavailable."""
        monkeypatch.setattr(interactive_module, "_HAS_QUESTIONARY", False)
        monkeypatch.setattr("typer.prompt", lambda msg, default="1": "1")
        result = interactive_module._select("Pick one:", ["a", "b", "c"])
        assert result in ["a", "b", "c"]

    def test_text_fallback(self, monkeypatch):
        """_text falls back to typer.prompt."""
        monkeypatch.setattr(interactive_module, "_HAS_QUESTIONARY", False)
        monkeypatch.setattr("typer.prompt", lambda msg, default="": "hello")
        result = interactive_module._text("Enter something:")
        assert result == "hello"

    def test_confirm_fallback(self, monkeypatch):
        """_confirm falls back to typer.confirm."""
        monkeypatch.setattr(interactive_module, "_HAS_QUESTIONARY", False)
        monkeypatch.setattr("typer.confirm", lambda msg, default=True: True)
        result = interactive_module._confirm("Are you sure?")
        assert result is True


# ---------------------------------------------------------------------------
# Wizard flows (mocked prompts)
# ---------------------------------------------------------------------------


class TestWizardRun:
    def test_wizard_run_no_systems(self, monkeypatch):
        """Wizard run warns when no systems are registered."""
        monkeypatch.setattr(interactive_module, "_HAS_QUESTIONARY", False)

        with patch("aptdata.plugins.registry.list_systems", return_value=[]):
            warning_called = []
            original_warning = interactive_module._console.warning

            def mock_warning(msg):
                warning_called.append(msg)

            interactive_module._console.warning = mock_warning
            try:
                interactive_module._wizard_run()
            finally:
                interactive_module._console.warning = original_warning

        assert len(warning_called) > 0

    def test_wizard_run_with_system(self, monkeypatch):
        """Wizard run executes a system."""
        mock_sys = MagicMock()
        mock_sys_cls = MagicMock(return_value=mock_sys)

        monkeypatch.setattr(interactive_module, "_HAS_QUESTIONARY", False)

        with patch("aptdata.plugins.registry.list_systems", return_value=["my_sys"]):
            with patch("aptdata.plugins.registry.get", return_value=mock_sys_cls):
                with patch.object(interactive_module, "_select", side_effect=["my_sys", "dev"]):
                    with patch.object(interactive_module, "_confirm", return_value=False):
                        interactive_module._wizard_run()

        mock_sys.run.assert_called_once()


class TestWizardList:
    def test_wizard_list_systems(self, monkeypatch):
        """Wizard list shows systems table."""
        monkeypatch.setattr(interactive_module, "_HAS_QUESTIONARY", False)
        rendered = []

        with patch.object(interactive_module._console, "render", side_effect=rendered.append):
            with patch.object(interactive_module, "_select", return_value="Systems"):
                with patch("aptdata.plugins.registry.list_systems", return_value=["a_sys"]):
                    interactive_module._wizard_list()

    def test_wizard_list_plugins(self, monkeypatch):
        """Wizard list shows plugins table."""
        monkeypatch.setattr(interactive_module, "_HAS_QUESTIONARY", False)

        with patch.object(interactive_module._console, "render"):
            with patch.object(interactive_module, "_select", return_value="All plugins"):
                with patch(
                    "aptdata.plugins.plugin_manager.list_plugins",
                    return_value={"readers": ["r1"], "writers": ["w1"]},
                ):
                    interactive_module._wizard_list()


class TestWizardInspect:
    def test_wizard_inspect_no_plugins(self, monkeypatch):
        """Wizard inspect warns when no plugins registered."""
        monkeypatch.setattr(interactive_module, "_HAS_QUESTIONARY", False)
        warnings = []

        with patch.object(interactive_module._console, "warning", side_effect=warnings.append):
            with patch("aptdata.plugins.plugin_manager.list_readers", return_value=[]):
                with patch("aptdata.plugins.plugin_manager.list_writers", return_value=[]):
                    interactive_module._wizard_inspect()

        assert len(warnings) > 0

    def test_wizard_inspect_with_plugin(self, monkeypatch):
        """Wizard inspect shows schema for a plugin."""
        schema = {"name": "r1", "type": "reader", "arguments": []}
        monkeypatch.setattr(interactive_module, "_HAS_QUESTIONARY", False)

        with patch.object(interactive_module._console, "render"):
            with patch.object(interactive_module, "_select", return_value="r1"):
                with patch("aptdata.plugins.plugin_manager.list_readers", return_value=["r1"]):
                    with patch("aptdata.plugins.plugin_manager.list_writers", return_value=[]):
                        with patch(
                            "aptdata.plugins.plugin_manager.get_plugin_schema",
                            return_value=schema,
                        ):
                            interactive_module._wizard_inspect()


class TestWizardTelemetry:
    def test_wizard_telemetry(self, monkeypatch):
        """Wizard telemetry shows status table."""
        monkeypatch.setattr(interactive_module, "_HAS_QUESTIONARY", False)
        rendered = []

        with patch.object(interactive_module._console, "render", side_effect=rendered.append):
            with patch.object(interactive_module, "_confirm", return_value=False):
                interactive_module._wizard_telemetry()

        assert len(rendered) == 1


# ---------------------------------------------------------------------------
# interactive command (CLI entry point) — mocked to exit immediately
# ---------------------------------------------------------------------------


class TestInteractiveCommand:
    def test_interactive_command_exits_on_exit_choice(self, monkeypatch):
        """interactive_command exits the loop on '❌ Exit' selection."""
        monkeypatch.setattr(interactive_module, "_HAS_QUESTIONARY", False)

        with patch.object(interactive_module, "_select", return_value="❌ Exit"):
            with patch.object(interactive_module._console, "rule"):
                with patch.object(interactive_module._console, "success"):
                    # Should return without raising
                    interactive_module.interactive_command()
