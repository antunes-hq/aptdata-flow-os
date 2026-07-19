"""Tests for agent adapter discovery via entry points (ADR-002 §2.1).

Covers:
* the built-in ``aptdata.agents`` entry points are discoverable and load
  into the right adapter classes;
* the lazy ``ADAPTERS`` cache is populated on first access and reset by
  :func:`_reset_adapters_cache`;
* broken entry points are surfaced as warnings and skipped (never raise);
* unknown ``spec.type`` values still fall back to :class:`_PlaceholderAgent`
  (which is itself registered as an entry point so the fallback is
  addressable by name too).
"""

from __future__ import annotations

import logging
from typing import Any

import pytest

from aptdata.agents.anthropic import AnthropicAgent
from aptdata.agents.base import AgentSpec, BaseAgent
from aptdata.agents.cli_agents import ClaudeCodeAgent, OpenCodeAgent
from aptdata.agents.openclaw import OpenClawAgent
from aptdata.agents.registry import (
    AGENT_ENTRY_POINT_GROUP,
    _build_agent,
    _discover_adapters,
    _PlaceholderAgent,
    _reset_adapters_cache,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeEP:
    """Minimal duck-typed stand-in for :class:`importlib.metadata.EntryPoint`.

    The real EntryPoint is immutable, so we can't patch its ``load`` method.
    This fake exposes the same surface used by the registry
    (``name`` / ``value`` / ``load()``).
    """

    def __init__(
        self,
        name: str,
        value: str,
        *,
        load_raises: BaseException | None = None,
        load_result: Any = None,
    ) -> None:
        self.name = name
        self.value = value
        self.group = AGENT_ENTRY_POINT_GROUP
        self._load_raises = load_raises
        self._load_result = load_result

    def load(self) -> Any:
        if self._load_raises is not None:
            raise self._load_raises
        if self._load_result is not None:
            return self._load_result
        # Default behaviour: actually resolve ``module:attr`` so the fake
        # behaves like a real entry point when no stub is configured.
        module_path, _, attr = self.value.partition(":")
        mod = __import__(module_path, fromlist=[attr])
        return getattr(mod, attr)


def _spec(type_: str, agent_id: str = "x") -> AgentSpec:
    return AgentSpec(id=agent_id, name=agent_id, type=type_)


def _patch_entry_points(monkeypatch: pytest.MonkeyPatch, eps: list[_FakeEP]) -> None:
    """Replace ``entry_points`` in the registry module with a stub returning *eps*."""

    def _fake_eps(*, group: str) -> list[_FakeEP]:
        if group == AGENT_ENTRY_POINT_GROUP:
            return list(eps)
        return []

    import aptdata.agents.registry as registry_mod

    monkeypatch.setattr(registry_mod, "entry_points", _fake_eps)


@pytest.fixture(autouse=True)
def _reset_cache_between_tests():
    """Ensure each test sees a clean adapter cache."""
    _reset_adapters_cache()
    yield
    _reset_adapters_cache()


# ---------------------------------------------------------------------------
# Discovery (real entry points declared in pyproject.toml)
# ---------------------------------------------------------------------------


class TestDiscoverAdapters:
    def test_discovers_all_built_in_adapters(self):
        adapters = _discover_adapters()

        # The five entry points declared in pyproject.toml
        assert set(adapters) >= {
            "anthropic",
            "openclaw",
            "claude_code",
            "opencode",
            "placeholder",
        }

    def test_built_in_adapters_are_the_right_classes(self):
        adapters = _discover_adapters()
        assert adapters["anthropic"] is AnthropicAgent
        assert adapters["openclaw"] is OpenClawAgent
        assert adapters["claude_code"] is ClaudeCodeAgent
        assert adapters["opencode"] is OpenCodeAgent
        assert adapters["placeholder"] is _PlaceholderAgent

    def test_all_discovered_are_baseagent_subclasses(self):
        adapters = _discover_adapters()
        for name, cls in adapters.items():
            assert isinstance(cls, type), f"{name!r} is not a class"
            assert issubclass(cls, BaseAgent), f"{name!r} ({cls!r}) is not a BaseAgent"

    def test_lazy_cache_populated_once(self, monkeypatch):
        """Successive calls return the same cached dict without re-discovering."""
        call_count = 0

        def _counting_eps(*, group: str) -> list[_FakeEP]:
            nonlocal call_count
            if group == AGENT_ENTRY_POINT_GROUP:
                call_count += 1
                return []
            return []

        import aptdata.agents.registry as registry_mod

        monkeypatch.setattr(registry_mod, "entry_points", _counting_eps)

        first = _discover_adapters()
        second = _discover_adapters()

        assert first is second
        assert (
            call_count == 1
        ), "entry_points should not be re-read after cache is populated"

    def test_adapters_module_attr_returns_discovered_dict(self):
        """PEP 562 ``__getattr__`` exposes ADAPTERS as the discovered dict."""
        import aptdata.agents.registry as registry_mod

        assert registry_mod.ADAPTERS is _discover_adapters()

    def test_adapters_module_attr_unknown_raises(self):
        import aptdata.agents.registry as registry_mod

        with pytest.raises(AttributeError, match="has no attribute"):
            _ = registry_mod.this_does_not_exist  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Fallback behaviour
# ---------------------------------------------------------------------------


class TestDiscoveryFallback:
    def test_broken_entry_point_skipped_with_warning(self, monkeypatch, caplog):
        broken = _FakeEP(
            "broken_backend",
            "nonexistent.pkg:Thing",
            load_raises=ImportError("nope"),
        )
        good = _FakeEP("anthropic", "aptdata.agents.anthropic:AnthropicAgent")
        _patch_entry_points(monkeypatch, [broken, good])

        with caplog.at_level(logging.WARNING, logger="aptdata.agents.registry"):
            adapters = _discover_adapters()

        assert "anthropic" in adapters
        assert "broken_backend" not in adapters
        assert any("broken_backend" in rec.message for rec in caplog.records)

    def test_non_baseagent_entry_point_skipped(self, monkeypatch, caplog):
        """An entry point whose loaded value is not a BaseAgent subclass is rejected."""
        non_agent = _FakeEP(
            "not_an_agent",
            "collections:OrderedDict",
            load_result=__import__("collections").OrderedDict,
        )
        _patch_entry_points(monkeypatch, [non_agent])

        with caplog.at_level(logging.WARNING, logger="aptdata.agents.registry"):
            adapters = _discover_adapters()

        assert "not_an_agent" not in adapters
        assert any("not a BaseAgent subclass" in rec.message for rec in caplog.records)

    def test_entry_points_call_failure_logged_and_returns_empty(
        self, monkeypatch, caplog
    ):
        def _broken_eps(*, group: str) -> list[_FakeEP]:
            raise RuntimeError("metadata exploded")

        import aptdata.agents.registry as registry_mod

        monkeypatch.setattr(registry_mod, "entry_points", _broken_eps)

        with caplog.at_level(logging.WARNING, logger="aptdata.agents.registry"):
            adapters = _discover_adapters()

        assert adapters == {}
        assert any(
            "Failed to read entry points group" in rec.message for rec in caplog.records
        )

    def test_unknown_type_falls_back_to_placeholder_agent(self):
        """A spec with no matching entry point still builds — as a Placeholder."""
        agent = _build_agent(_spec("totally_unknown_kind_xyz", agent_id="ghost"))
        assert isinstance(agent, _PlaceholderAgent)
        result = agent.send("oi")
        assert result.ok is False
        assert "totally_unknown_kind_xyz" in (result.error or "")

    def test_placeholder_entry_point_addressable(self):
        """The placeholder is itself registered as an entry point — so it can be
        explicitly named in agents.yaml when a backend is intentionally a stub."""
        adapters = _discover_adapters()
        assert adapters["placeholder"] is _PlaceholderAgent
        agent = _build_agent(_spec("placeholder", agent_id="stub"))
        assert isinstance(agent, _PlaceholderAgent)

    def test_reset_cache_forces_rediscovery(self, monkeypatch):
        """After _reset_adapters_cache, the next call re-runs entry_points."""
        call_count = 0

        def _counting_eps(*, group: str) -> list[_FakeEP]:
            nonlocal call_count
            if group == AGENT_ENTRY_POINT_GROUP:
                call_count += 1
                return []
            return []

        import aptdata.agents.registry as registry_mod

        monkeypatch.setattr(registry_mod, "entry_points", _counting_eps)

        _discover_adapters()
        _reset_adapters_cache()
        _discover_adapters()

        assert call_count == 2


# ---------------------------------------------------------------------------
# Build-agent integration with the real (built-in) entry points
# ---------------------------------------------------------------------------


class TestBuildAgentWithRealEntryPoints:
    def test_build_anthropic_adapter(self):
        agent = _build_agent(_spec("anthropic", agent_id="claude"))
        assert isinstance(agent, AnthropicAgent)
        assert agent.id == "claude"

    def test_build_openclaw_adapter(self):
        agent = _build_agent(_spec("openclaw", agent_id="ondina"))
        assert isinstance(agent, OpenClawAgent)

    def test_build_cli_adapters(self):
        cc = _build_agent(_spec("claude_code", agent_id="cc"))
        oc = _build_agent(_spec("opencode", agent_id="oc"))
        assert isinstance(cc, ClaudeCodeAgent)
        assert isinstance(oc, OpenCodeAgent)
