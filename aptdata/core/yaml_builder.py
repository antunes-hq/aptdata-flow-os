import importlib.util
import logging
import os
import sys
from typing import Any

import yaml

from aptdata.core.registry import ComponentRegistry
from aptdata.core.system import BaseFlow, BaseSystem

logger = logging.getLogger(__name__)


class YamlSystemBuilder:
    """Builds a BaseSystem from a YAML manifest.

    This orchestrator resolves components from the ComponentRegistry.
    """

    def __init__(self, yaml_path: str):
        self.yaml_path = os.path.abspath(yaml_path)
        with open(self.yaml_path) as f:
            self.manifest = yaml.safe_load(f)

    def load_component_modules(self, module_paths: list[str]) -> None:
        """Dynamically load python modules so their decorators execute and register
        components."""
        yaml_dir = os.path.dirname(self.yaml_path)

        for idx, mod_path in enumerate(module_paths):
            # Resolve relative paths relative to the yaml file
            if not os.path.isabs(mod_path):
                mod_path = os.path.join(yaml_dir, mod_path)

            module_name = f"yaml_component_module_{idx}"
            spec = importlib.util.spec_from_file_location(module_name, mod_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                logger.debug(f"Loaded component module: {mod_path}")
            else:
                logger.error(f"Failed to load module: {mod_path}")

    def build(self) -> BaseSystem:
        """Build and return the BaseSystem configured in the YAML manifest."""
        if "system" not in self.manifest:
            raise ValueError("YAML manifest must contain a 'system' block.")

        sys_config = self.manifest["system"]
        system_id = sys_config.get("id", "yaml_system")

        # Load custom Python modules if specified (to populate registry)
        if "imports" in self.manifest:
            self.load_component_modules(self.manifest["imports"])

        # Create system class
        class DynamicSystem(BaseSystem):
            def setup(self) -> None:
                # Optionally init telemetry if the manifest asks for it
                if sys_config.get("telemetry", False):
                    from aptdata.telemetry import TelemetryProvider

                    self.telemetry = TelemetryProvider.get_instance()

            def on_complete(self, context: Any) -> None:
                if sys_config.get("export_lineage", False):
                    # Emulate lineage logic
                    context.logger.info("Lineage exported (mocked for YAML builder)")

        system = DynamicSystem(system_id=system_id)

        # Build flows
        flows_config = sys_config.get("flows", [])
        for flow_config in flows_config:
            flow_id = flow_config.get("id")
            if not flow_id:
                raise ValueError("Each flow must have an 'id'.")

            class DynamicFlow(BaseFlow):
                def __init__(self, **kwargs):
                    # We store configs to build later during the build() lifecycle phase
                    self._yaml_components_config = kwargs.pop("components_config", [])
                    self._yaml_connections = kwargs.pop("connections_config", [])
                    super().__init__(**kwargs)

                def build(self) -> None:
                    # Look up and add components
                    for comp_config in self._yaml_components_config:
                        name = comp_config.get("name")
                        ref = comp_config.get("ref")

                        if not name or not ref:
                            raise ValueError(
                                "Each component must have a 'name' and 'ref'."
                            )

                        # Lookup in registry
                        component_class = ComponentRegistry.get(ref)

                        # Instantiate with name from YAML
                        # For dynamic components, component_id must be correctly set
                        params = comp_config.get("params", {})
                        comp_instance = component_class(component_id=name, **params)

                        # Add to flow (No output contract handling here for simplicity,
                        # but could load via import string)
                        self.add_component(comp_instance)

                    # Parse connections
                    for conn in self._yaml_connections:
                        source = conn.get("from")
                        target = conn.get("to")
                        if source and target:
                            self.connect(source_id=source, target_id=target)

            flow = DynamicFlow(
                flow_id=flow_id,
                components_config=flow_config.get("components", []),
                connections_config=flow_config.get("connections", []),
            )

            system.register_flow(flow)

        return system
