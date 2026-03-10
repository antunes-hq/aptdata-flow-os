"""YAML parser for declarative aptdata system definitions."""

from __future__ import annotations

from dataclasses import field
from pathlib import Path
from typing import Any

import yaml
from pydantic import TypeAdapter
from pydantic.dataclasses import dataclass as pydantic_dataclass

from aptdata.config.secrets import SecretManager
from aptdata.core.dataset import IDataset
from aptdata.core.system import BaseComponent, BaseFlow, BaseSystem, IFlow


@pydantic_dataclass
class ConfigEdge:
    """Serializable flow edge for declarative YAML files."""

    source_id: str
    target_id: str
    condition: str = ""


@pydantic_dataclass
class ConfigComponent(BaseComponent):
    """Concrete component used by configuration hydration."""

    def validate_inputs(self, inputs: list[IDataset]) -> bool:  # noqa: ARG002
        return True

    def execute(self, inputs: list[IDataset]) -> list[IDataset]:
        return inputs


@pydantic_dataclass
class ConfigFlow(BaseFlow):
    """Concrete flow used by configuration hydration."""

    components: list[ConfigComponent] = field(default_factory=list)
    edges: list[ConfigEdge] = field(default_factory=list)

    def add_component(self, component: BaseComponent) -> None:
        if not isinstance(component, ConfigComponent):
            raise TypeError("ConfigFlow only accepts ConfigComponent instances.")
        self.components.append(component)

    def connect(
        self,
        source_id: str,
        target_id: str,
        condition: str | None = None,
    ) -> None:
        self.edges.append(
            ConfigEdge(
                source_id=source_id,
                target_id=target_id,
                condition=condition or "",
            )
        )

    def compile(self) -> None:
        pass

    def run(self, initial_inputs: list[IDataset]) -> list[IDataset]:
        return initial_inputs


@pydantic_dataclass
class ConfigSystem(BaseSystem):
    """Concrete system used by configuration hydration."""

    flows: list[ConfigFlow] = field(default_factory=list)

    def register_flow(self, flow: IFlow) -> None:
        if not isinstance(flow, ConfigFlow):
            raise TypeError("ConfigSystem only accepts ConfigFlow instances.")
        self.flows.append(flow)

    def run(self) -> None:
        pass


@pydantic_dataclass
class ParsedConfig:
    """Hydrated config document with metadata and validated domain objects."""

    metadata: dict[str, Any] = field(default_factory=dict)
    system: ConfigSystem = field(
        default_factory=lambda: ConfigSystem(system_id="default")
    )


class YamlConfigParser:
    """Parse YAML files into validated aptdata domain objects."""

    _component_adapter = TypeAdapter(ConfigComponent)
    _flow_adapter = TypeAdapter(ConfigFlow)
    _edge_adapter = TypeAdapter(ConfigEdge)
    _system_adapter = TypeAdapter(ConfigSystem)

    def __init__(self, secret_manager: SecretManager | None = None) -> None:
        self._secret_manager = secret_manager or SecretManager()

    def parse_file(self, path: str | Path) -> ParsedConfig:
        """Read and parse a YAML config file."""
        config_path = Path(path)
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError("YAML root must be a mapping/object.")
        return self.parse_data(raw)

    def parse_data(self, payload: dict[str, Any]) -> ParsedConfig:
        """Parse a loaded YAML dictionary."""
        payload = self._secret_manager.resolve(payload)
        metadata = payload.get("metadata", {})
        system_payload = dict(payload.get("system", {}))
        flow_payloads = system_payload.pop("flows", payload.get("flows", []))

        system = self._system_adapter.validate_python(system_payload)
        for flow_payload in flow_payloads:
            flow_data = dict(flow_payload)
            component_payloads = flow_data.pop("components", [])
            edge_payloads = flow_data.pop("edges", [])

            flow = self._flow_adapter.validate_python(flow_data)
            for component_payload in component_payloads:
                component = self._component_adapter.validate_python(component_payload)
                flow.add_component(component)
            for edge_payload in edge_payloads:
                flow.edges.append(self._edge_adapter.validate_python(edge_payload))
            system.register_flow(flow)

        return ParsedConfig(metadata=metadata, system=system)
