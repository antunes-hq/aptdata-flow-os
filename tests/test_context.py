"""Tests for execution context state container."""

from smart_data.core.context import ExecutionContext


class TestExecutionContext:
    def test_set_get_update_clear(self):
        context = ExecutionContext()
        context.set("conversation_id", "abc")
        assert context.get("conversation_id") == "abc"

        context.update({"turn": 1, "active": True})
        assert context.get("turn") == 1
        assert context.get("active") is True
        assert context.get("missing", "fallback") == "fallback"

        context.clear()
        assert context.memory == {}
