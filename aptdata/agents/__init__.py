"""aptdata.agents — uniform interface over heterogeneous agent backends.

The single source of truth for the multi-agent ecosystem: one declarative
registry (``agents.yaml``), one :class:`IAgent` contract, one adapter per
backend kind.
"""

from __future__ import annotations

from aptdata.agents.base import (
    AgentHealth,
    AgentResponse,
    AgentSpec,
    BaseAgent,
    IAgent,
)
from aptdata.agents.openclaw import OpenClawAgent
from aptdata.agents.project import (
    Project,
    ProjectRunner,
    Task,
    TaskResult,
    scaffold_project,
)
from aptdata.agents.registry import ADAPTERS, AgentRegistry
from aptdata.agents.router import RouteDecision, Router, Skill

__all__ = [
    "ADAPTERS",
    "AgentHealth",
    "AgentRegistry",
    "AgentResponse",
    "AgentSpec",
    "BaseAgent",
    "IAgent",
    "OpenClawAgent",
    "Project",
    "ProjectRunner",
    "RouteDecision",
    "Router",
    "Skill",
    "Task",
    "TaskResult",
    "scaffold_project",
]
