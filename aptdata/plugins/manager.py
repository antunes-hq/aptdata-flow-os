"""Dynamic plugin manager for aptdata.

Provides :class:`PluginManager` which can discover, register, and
instantiate reader / writer plugins.  If a plugin requires an
optional third-party library that is not installed, a friendly
:class:`PluginDependencyError` is raised.
"""

from __future__ import annotations

import importlib
import inspect
from typing import Any

from aptdata.plugins.base import BaseReader, BaseWriter

# ---------------------------------------------------------------------------
# Custom errors
# ---------------------------------------------------------------------------


class PluginDependencyError(ImportError):
    """Raised when a plugin requires a library that is not installed."""

    def __init__(self, plugin_name: str, package: str) -> None:
        self.plugin_name = plugin_name
        self.package = package
        super().__init__(
            f"Plugin '{plugin_name}' requires the '{package}' package. "
            f"Install it with:  pip install {package}"
        )


# ---------------------------------------------------------------------------
# Plugin Manager
# ---------------------------------------------------------------------------


class PluginManager:
    """Registry for reader / writer plugin classes.

    Plugins are registered under a unique *name* and can be retrieved or
    listed later.  The manager also supports loading a plugin module by
    its dotted Python path so that dynamic/entry-point-style discovery is
    straightforward.
    """

    def __init__(self) -> None:
        self._readers: dict[str, type[BaseReader]] = {}
        self._writers: dict[str, type[BaseWriter]] = {}

    # -- registration -------------------------------------------------------

    def register_reader(self, name: str, reader_cls: type[BaseReader]) -> None:
        """Register *reader_cls* under *name*."""
        self._readers[name] = reader_cls

    def register_writer(self, name: str, writer_cls: type[BaseWriter]) -> None:
        """Register *writer_cls* under *name*."""
        self._writers[name] = writer_cls

    # -- lookup -------------------------------------------------------------

    def get_reader(self, name: str) -> type[BaseReader] | None:
        """Return the reader class registered under *name*, or ``None``."""
        return self._readers.get(name)

    def get_writer(self, name: str) -> type[BaseWriter] | None:
        """Return the writer class registered under *name*, or ``None``."""
        return self._writers.get(name)

    # -- listing ------------------------------------------------------------

    def list_readers(self) -> list[str]:
        """Return a sorted list of registered reader names."""
        return sorted(self._readers)

    def list_writers(self) -> list[str]:
        """Return a sorted list of registered writer names."""
        return sorted(self._writers)

    def list_plugins(self) -> dict[str, list[str]]:
        """Return all registered plugins grouped by kind."""
        return {
            "readers": self.list_readers(),
            "writers": self.list_writers(),
        }

    def get_plugin_schema(self, name: str) -> dict[str, Any]:
        """Return constructor argument schema for a reader/writer plugin."""
        plugin_cls: type[Any] | None = self.get_reader(name) or self.get_writer(name)
        if plugin_cls is None:
            raise KeyError(f"Plugin '{name}' is not registered.")

        signature = inspect.signature(plugin_cls.__init__)
        args: list[dict[str, Any]] = []
        for param_name, param in signature.parameters.items():
            if param_name == "self":
                continue
            args.append(
                {
                    "name": param_name,
                    "required": param.default is inspect.Parameter.empty,
                    "default": None if param.default is inspect.Parameter.empty else param.default,
                }
            )

        plugin_type = "reader" if self.get_reader(name) is not None else "writer"
        return {"name": name, "type": plugin_type, "arguments": args}

    def preview_dataset(self, plugin_name: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Run a reader plugin and return the first five records."""
        reader_cls = self.get_reader(plugin_name)
        if reader_cls is None:
            raise KeyError(f"Reader plugin '{plugin_name}' is not registered.")
        reader = reader_cls(**kwargs)
        dataset = reader.read()
        records = dataset.read()
        return records[:5]

    # -- dynamic loading ----------------------------------------------------

    def load_module(self, module_path: str) -> Any:
        """Import *module_path* and return the module object.

        This is useful for loading plugin modules dynamically, e.g. from
        an entry-point or a configuration file.

        Raises
        ------
        ModuleNotFoundError
            If the module cannot be imported.
        """
        return importlib.import_module(module_path)


#: Global singleton – import this in plugin modules and application code.
plugin_manager = PluginManager()

__all__ = ["PluginManager", "PluginDependencyError", "plugin_manager"]
