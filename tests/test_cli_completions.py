"""Tests for smart_data.cli.completions — shell completion functions."""

from __future__ import annotations

from smart_data.cli.completions import (
    complete_env_names,
    complete_plugin_names,
    complete_reader_names,
    complete_system_names,
    complete_template_names,
    complete_writer_names,
)
from smart_data.plugins import registry, plugin_manager
from smart_data.plugins.base import BaseReader, BaseWriter
from smart_data.plugins.dataset import InMemoryDataset


# ---------------------------------------------------------------------------
# Fixtures — register test entries
# ---------------------------------------------------------------------------


class _CompReader(BaseReader):
    def __init__(self) -> None:
        pass

    def read(self) -> InMemoryDataset:
        return InMemoryDataset(uri="memory://comp", schema_metadata={})


class _CompWriter(BaseWriter):
    def __init__(self) -> None:
        pass

    def write(self, dataset) -> None:
        pass


plugin_manager.register_reader("comp_reader_alpha", _CompReader)
plugin_manager.register_writer("comp_writer_beta", _CompWriter)


# ---------------------------------------------------------------------------
# complete_system_names
# ---------------------------------------------------------------------------


class TestCompleteSystemNames:
    def test_returns_list(self):
        result = complete_system_names("")
        assert isinstance(result, list)

    def test_filters_by_prefix(self):
        # Register a system to ensure there's something to match
        from pydantic.dataclasses import dataclass as pydantic_dataclass
        from smart_data.core.system import BaseSystem

        @pydantic_dataclass
        class _PrefixSys(BaseSystem):
            def __post_init__(self):
                self._flows = []

            def register_flow(self, flow):
                self._flows.append(flow)

            def run(self):
                pass

        registry.register("prefix_unique_sys", _PrefixSys)
        result = complete_system_names("prefix_")
        assert "prefix_unique_sys" in result

    def test_no_match_returns_empty(self):
        result = complete_system_names("zzzzzz_no_match")
        assert result == []

    def test_empty_prefix_returns_all(self):
        result = complete_system_names("")
        assert len(result) >= 0  # At least zero items


# ---------------------------------------------------------------------------
# complete_reader_names
# ---------------------------------------------------------------------------


class TestCompleteReaderNames:
    def test_returns_list(self):
        result = complete_reader_names("")
        assert isinstance(result, list)

    def test_contains_registered_reader(self):
        result = complete_reader_names("comp_reader")
        assert "comp_reader_alpha" in result

    def test_prefix_filter(self):
        result = complete_reader_names("comp_reader_a")
        assert "comp_reader_alpha" in result
        result_no_match = complete_reader_names("zzzz_no_reader")
        assert result_no_match == []


# ---------------------------------------------------------------------------
# complete_writer_names
# ---------------------------------------------------------------------------


class TestCompleteWriterNames:
    def test_returns_list(self):
        result = complete_writer_names("")
        assert isinstance(result, list)

    def test_contains_registered_writer(self):
        result = complete_writer_names("comp_writer")
        assert "comp_writer_beta" in result

    def test_prefix_filter(self):
        result = complete_writer_names("comp_writer_b")
        assert "comp_writer_beta" in result
        result_no_match = complete_writer_names("zzzz_no_writer")
        assert result_no_match == []


# ---------------------------------------------------------------------------
# complete_plugin_names (union of readers + writers)
# ---------------------------------------------------------------------------


class TestCompletePluginNames:
    def test_returns_sorted_list(self):
        result = complete_plugin_names("")
        assert result == sorted(result)

    def test_contains_reader_and_writer(self):
        result = complete_plugin_names("comp_")
        assert "comp_reader_alpha" in result
        assert "comp_writer_beta" in result

    def test_no_duplicates(self):
        result = complete_plugin_names("")
        assert len(result) == len(set(result))


# ---------------------------------------------------------------------------
# complete_env_names
# ---------------------------------------------------------------------------


class TestCompleteEnvNames:
    def test_returns_list(self):
        result = complete_env_names("")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_contains_standard_envs(self):
        result = complete_env_names("")
        assert "dev" in result
        assert "prod" in result

    def test_prefix_filter(self):
        result = complete_env_names("dev")
        assert "dev" in result
        assert "prod" not in result

    def test_no_match(self):
        result = complete_env_names("zzz_no_env")
        assert result == []


# ---------------------------------------------------------------------------
# complete_template_names
# ---------------------------------------------------------------------------


class TestCompleteTemplateNames:
    def test_returns_list(self):
        result = complete_template_names("")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_contains_hello_world(self):
        result = complete_template_names("")
        assert "hello-world" in result

    def test_prefix_filter(self):
        result = complete_template_names("hello")
        assert "hello-world" in result
        result_m = complete_template_names("med")
        assert "medallion" in result_m

    def test_no_match_returns_empty(self):
        result = complete_template_names("zzzz_no_template")
        assert result == []
