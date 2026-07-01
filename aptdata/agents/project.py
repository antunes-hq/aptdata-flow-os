"""Projects — a project is a Flow of agent tasks.

This is the bridge between aptdata's orchestration model and the multi-agent
ecosystem: a :class:`Project` is a declarative plan (a list of :class:`Task`),
and :class:`ProjectRunner` executes it by routing each task to the right agent
via the :class:`~aptdata.agents.router.Router`.

A project is persisted as ``<name>.project.yaml`` — editable by hand, runnable
by ``aptdata project run``. Each task can pin an explicit ``agent``, ask for a
``capability`` (routed to the best agent), or fall back to skill routing on its
``prompt``. ``depends_on`` lets a task be skipped when an upstream task fails.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from aptdata.agents.router import Router

logger = logging.getLogger(__name__)


class Task(BaseModel):
    """One step of a project, dispatched to a single agent."""

    id: str
    prompt: str
    capability: str | None = None  # route by capability
    agent: str | None = None  # pin an explicit agent (wins over capability)
    depends_on: list[str] = Field(default_factory=list)


class Project(BaseModel):
    """A declarative plan: an ordered list of agent tasks."""

    name: str
    description: str = ""
    tasks: list[Task] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> Project:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls(**raw)

    def to_yaml(self, path: str | Path) -> None:
        data = self.model_dump(exclude_defaults=False)
        Path(path).write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )


@dataclass
class TaskResult:
    """Outcome of running a single task."""

    task_id: str
    agent_id: str | None
    mode: str
    ok: bool
    text: str = ""
    error: str | None = None
    skipped: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "mode": self.mode,
            "ok": self.ok,
            "skipped": self.skipped,
            "error": self.error,
        }


class ProjectRunner:
    """Executes a :class:`Project` by routing every task through the Router."""

    def __init__(self, project: Project, router: Router) -> None:
        self.project = project
        self.router = router

    def _route_task(self, task: Task):
        """Decide which agent handles a task (explicit > capability > skill)."""
        from aptdata.agents.router import RouteDecision  # noqa: PLC0415

        if task.agent:
            if task.agent in self.router.registry:
                return RouteDecision(
                    agent_id=task.agent, mode="explicit", text=task.prompt,
                    confidence=1.0,
                )
            return RouteDecision(agent_id=None, mode="none", text=task.prompt)
        if task.capability:
            agent = self.router.registry.resolve(task.capability)
            if agent:
                return RouteDecision(
                    agent_id=agent.id, mode="capability", text=task.prompt,
                    confidence=0.9,
                )
        return self.router.route(task.prompt)

    def plan(self) -> list[TaskResult]:
        """Dry-run: resolve routing for every task without sending anything."""
        results: list[TaskResult] = []
        for task in self.project.tasks:
            decision = self._route_task(task)
            results.append(
                TaskResult(
                    task_id=task.id,
                    agent_id=decision.agent_id,
                    mode=decision.mode,
                    ok=decision.agent_id is not None,
                )
            )
        return results

    def run(self) -> list[TaskResult]:
        """Execute tasks in order, skipping those whose dependencies failed."""
        results: dict[str, TaskResult] = {}
        for task in self.project.tasks:
            failed_dep = next(
                (
                    d
                    for d in task.depends_on
                    if d not in results or not results[d].ok
                ),
                None,
            )
            if failed_dep is not None:
                results[task.id] = TaskResult(
                    task_id=task.id, agent_id=None, mode="skipped", ok=False,
                    skipped=True, error=f"dependency '{failed_dep}' unmet",
                )
                continue

            decision = self._route_task(task)
            if decision.agent_id is None:
                results[task.id] = TaskResult(
                    task_id=task.id, agent_id=None, mode=decision.mode, ok=False,
                    error="no agent could be routed",
                )
                continue

            response = self.router.registry.get(decision.agent_id).send(
                decision.text
            )
            results[task.id] = TaskResult(
                task_id=task.id,
                agent_id=decision.agent_id,
                mode=decision.mode,
                ok=response.ok,
                text=response.text,
                error=response.error,
            )
        return [results[t.id] for t in self.project.tasks]


def scaffold_project(name: str) -> Project:
    """Return a starter project with example tasks across capabilities."""
    return Project(
        name=name,
        description=f"Projeto {name} — orquestrado pelo aptdata.",
        tasks=[
            Task(id="planejar", prompt=f"Faz o plano técnico do {name}.",
                 capability="planning"),
            Task(id="backend", prompt="Implementa o backend / API.",
                 capability="backend", depends_on=["planejar"]),
            Task(id="frontend", prompt="Implementa a interface.",
                 capability="frontend", depends_on=["planejar"]),
            Task(id="deploy", prompt="Sobe em produção.",
                 capability="deploy", depends_on=["backend", "frontend"]),
        ],
    )
