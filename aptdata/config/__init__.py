"""Declarative configuration helpers for aptdata."""

from aptdata.config.loader import (
    APTDATA_DIR_NAME,
    LEGACY_TO_DOTDIR,
    SCHEMA_FILES,
    ProjectConfig,
    ProjectNotFoundError,
    detect_legacy_files,
    load_yaml_file,
    locate_project,
    locate_project_optional,
)
from aptdata.config.parser import ParsedConfig, YamlConfigParser
from aptdata.config.schema import (
    AgentsFile,
    SystemManifest,
    export_agents_schema,
    export_config_schema,
    export_domain_schema,
    export_system_schema,
    write_all_schemas,
    write_domain_schema,
    write_schema,
)
from aptdata.config.secrets import SecretManager

__all__ = [
    # Loader (.aptdata/ dotdir)
    "APTDATA_DIR_NAME",
    "LEGACY_TO_DOTDIR",
    "ProjectConfig",
    "ProjectNotFoundError",
    "SCHEMA_FILES",
    "detect_legacy_files",
    "load_yaml_file",
    "locate_project",
    "locate_project_optional",
    # Parser
    "ParsedConfig",
    "YamlConfigParser",
    # Schemas
    "AgentsFile",
    "SystemManifest",
    "export_agents_schema",
    "export_config_schema",
    "export_domain_schema",
    "export_system_schema",
    "write_all_schemas",
    "write_domain_schema",
    "write_schema",
    # Secrets
    "SecretManager",
]
