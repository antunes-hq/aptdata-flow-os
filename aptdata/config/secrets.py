"""Secret resolution helpers for aptdata configuration and plugins."""

from __future__ import annotations

import os
import re
from typing import Any

from aptdata.telemetry.instrumentation import register_secret

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z0-9_]+)\}")


class SecretManager:
    """Resolve `${ENV_VAR}` placeholders using environment variables."""

    def __init__(self, *, load_dotenv_file: bool = True) -> None:
        if load_dotenv_file:
            try:
                from dotenv import load_dotenv  # noqa: WPS433
            except ImportError:
                load_dotenv = None
            if load_dotenv is not None:
                load_dotenv(dotenv_path=".env")
        self._injected_keys: set[str] = set()

    def get(self, key: str, default: str | None = None) -> str:
        """Return environment value for *key* and register it as a secret."""
        value = os.getenv(key, default)
        if value is None:
            raise KeyError(f"Missing required secret: {key}")
        self._injected_keys.add(key)
        register_secret(key, value)
        return value

    def resolve(self, value: Any) -> Any:
        """Recursively resolve `${ENV_VAR}` placeholders in nested structures."""
        if isinstance(value, str):
            return self._resolve_string(value)
        if isinstance(value, dict):
            return {k: self.resolve(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.resolve(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self.resolve(item) for item in value)
        return value

    def injected_keys(self) -> list[str]:
        """Return sorted secret names injected in this manager session."""
        return sorted(self._injected_keys)

    def _resolve_string(self, value: str) -> str:
        matches = _ENV_PATTERN.findall(value)
        if not matches:
            return value
        resolved = value
        for key in matches:
            resolved_secret = self.get(key)
            resolved = resolved.replace(f"${{{key}}}", resolved_secret)
        return resolved
