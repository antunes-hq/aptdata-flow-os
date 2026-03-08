"""Tests for smart_data.config.secrets."""

from __future__ import annotations

from smart_data.config.secrets import SecretManager


class TestSecretManager:
    def test_get_reads_env_and_tracks_key(self, monkeypatch):
        monkeypatch.setenv("API_TOKEN", "token-123")
        manager = SecretManager(load_dotenv_file=False)
        assert manager.get("API_TOKEN") == "token-123"
        assert manager.injected_keys() == ["API_TOKEN"]

    def test_resolve_replaces_placeholders_recursively(self, monkeypatch):
        monkeypatch.setenv("AUTH_TOKEN", "secret-token")
        manager = SecretManager(load_dotenv_file=False)
        resolved = manager.resolve(
            {
                "headers": {"Authorization": "Bearer ${AUTH_TOKEN}"},
                "list": ["${AUTH_TOKEN}"],
            }
        )
        assert resolved["headers"]["Authorization"] == "Bearer secret-token"
        assert resolved["list"] == ["secret-token"]

    def test_loads_dotenv_when_enabled(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("DOTENV_SECRET=from-dotenv\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        manager = SecretManager(load_dotenv_file=True)
        assert manager.get("DOTENV_SECRET") == "from-dotenv"
