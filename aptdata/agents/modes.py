"""ExecutionMode — vocabulário de 1ª classe para "como o aptdata executa".

A ADR-002 §2.3 pede que os **modos de execução** deixem de ser conhecimento
implícito no código e virem nomeados, documentados e expostos no CLI / ``.aptdata/``.
Este módulo centraliza esse vocabulário.

O ``ExecutionMode`` é um eixo **novo** por cima dos três já existentes:

* :class:`~aptdata.agents.router.RouteDecision.mode` — *como* o roteamento
  decidiu o alvo (``prefix``/``skill``/``llm``/``default``/``none``).
* :class:`~aptdata.agents.project.TaskResult.mode` — *como* uma task foi
  roteada (``explicit``/``capability``/``skipped``/``<decision.mode>``).
* :class:`~aptdata.agents.conversation.Turn.type` — *qual* o outcome de um
  turno de conversa (``dispatched``/``needs_confirmation``/``needs_clarification``).

Esses três descrevem dimensões internas da orquestração e seguem úteis; o
``ExecutionMode`` descreve o **tipo de execução** que o usuário pediu ao
aptdata — uma camada de produto, alinhada à ADR-002 §2.3.
"""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple


class ExecutionMode(str, Enum):
    """Os 4 modos canônicos de execução do aptdata.

    Cada valor é a string que aparece no CLI (``--mode``), no ``.aptdata/agents.yaml``
    (``default_mode:``) e no campo ``mode`` de toda saída ``--json`` de um
    comando de execução — mantendo o contrato machine-readable do resto do CLI.
    """

    ONESHOT = "oneshot"
    """Um único :meth:`~aptdata.agents.base.IAgent.send` a um agente resolvido
    por id (``aptdata agents send``). Sem roteamento, sem sessão, sem plano —
    "fala com este agente e devolve a resposta"."""

    CONVERSE = "converse"
    """Sessão multi-turno via :class:`~aptdata.agents.conversation.ConversationEngine`:
    roteia, pede confirmação quando a confiança é média, lembra do último
    agente da sessão. Comando: ``aptdata converse``."""

    PROJECT = "project"
    """Execução orientada a tarefas via :class:`~aptdata.agents.project.Project`
    / :class:`~aptdata.agents.project.ProjectRunner`: cada task roteia para o
    agente certo (``agent`` / ``capability`` / skill), com ``depends_on``.
    Comando: ``aptdata project run``."""

    ORCHESTRATED = "orchestrated"
    """Roteamento multi-agente pelo :class:`~aptdata.agents.router.Router`
    (prefix / skill / llm / default + confiança). É o "deixa o aptdata
    escolher o agente e despachar". Comandos: ``aptdata agents dispatch`` e
    ``aptdata agents route`` (este último é um dry-run implícito — só mostra
    a decisão, não despacha)."""

    # -- pydantic / json ----------------------------------------------------

    @classmethod
    def from_str(cls, value: str) -> ExecutionMode:
        """Parse tolerante: aceita o valor canônico (``"oneshot"``) ou o nome
        do membro (``"ONESHOT"``), case-insensitive."""
        if isinstance(value, cls):
            return value
        normalized = value.strip().lower()
        for member in cls:
            if member.value == normalized or member.name.lower() == normalized:
                return member
        raise ValueError(
            f"Unknown execution mode: {value!r}. "
            f"Choose one of {[m.value for m in cls]}"
        )

    def __str__(self) -> str:
        # str(ExecutionMode.ONESHOT) == "oneshot" — assim o json.dumps() e o
        # typer usam o valor canônico, não "ExecutionMode.ONESHOT".
        return self.value


# ---------------------------------------------------------------------------
# Mapeamento CLI → modo (a fonte de verdade do default de cada comando)
# ---------------------------------------------------------------------------


class ModeDoc(NamedTuple):
    """Metadados de um modo — usado por ``aptdata modes list`` e pela docs."""

    mode: ExecutionMode
    short: str
    description: str
    cli_command: str


MODE_DOCS: tuple[ModeDoc, ...] = (
    ModeDoc(
        mode=ExecutionMode.ONESHOT,
        short="Send único a um agente",
        description=(
            "Envia um prompt a um agente resolvido por id e devolve a "
            "resposta. Sem roteamento, sem sessão, sem plano — o caminho "
            "mais direto para falar com um backend específico."
        ),
        cli_command="aptdata agents send AGENT_ID PROMPT",
    ),
    ModeDoc(
        mode=ExecutionMode.CONVERSE,
        short="Sessão multi-turno",
        description=(
            "ConversationEngine: roteia, pede confirmação quando a "
            "confiança é média, lembra do último agente da sessão e "
            "persiste o estado em ~/.aptdata/sessions."
        ),
        cli_command="aptdata converse TEXT",
    ),
    ModeDoc(
        mode=ExecutionMode.PROJECT,
        short="Plano de tarefas roteadas",
        description=(
            "Executa um *.project.yaml — cada task é roteada para o agente "
            "certo (agent/capability/skill), respeitando depends_on. "
            "Preview com `aptdata project plan`."
        ),
        cli_command="aptdata project run PROJECT_FILE",
    ),
    ModeDoc(
        mode=ExecutionMode.ORCHESTRATED,
        short="Roteamento multi-agente",
        description=(
            "Deixa o Router escolher o agente (prefix/skill/llm/default + "
            "confiança) e despachar. `aptdata agents route` é o dry-run "
            "implícito deste modo — só mostra a decisão."
        ),
        cli_command="aptdata agents dispatch TEXT",
    ),
)


#: Mapa ``("group", "command")`` → modo natural (default do ``--mode``).
#: ``None`` significa "sem default; use o ``default_mode`` do projeto se houver".
_COMMAND_DEFAULTS: dict[tuple[str, str], ExecutionMode] = {
    ("agents", "send"): ExecutionMode.ONESHOT,
    ("agents", "dispatch"): ExecutionMode.ORCHESTRATED,
    ("agents", "route"): ExecutionMode.ORCHESTRATED,
    ("converse", ""): ExecutionMode.CONVERSE,  # top-level command
    ("project", "run"): ExecutionMode.PROJECT,
    ("project", "plan"): ExecutionMode.PROJECT,
}


def mode_for_command(group: str, command: str = "") -> ExecutionMode | None:
    """Retorna o modo natural de um comando CLI (``("agents", "send")`` → ``ONESHOT``).

    Retorna ``None`` quando o comando não tem default natural — o caller deve
    então cair no ``default_mode`` do ``.aptdata/agents.yaml`` (se houver).
    """
    return _COMMAND_DEFAULTS.get((group, command))


def resolve_mode(
    explicit: str | ExecutionMode | None,
    group: str,
    command: str = "",
    project_default: ExecutionMode | None = None,
) -> ExecutionMode:
    """Resolve o modo efetivo: ``--mode`` > default do projeto > default do comando.

    Parameters
    ----------
    explicit:
        Valor passado via ``--mode`` (string ou enum). ``None`` = não setado.
    group, command:
        Chave do comando no mapa ``_COMMAND_DEFAULTS`` (ex.: ``("agents", "send")``).
    project_default:
        Valor de ``default_mode`` do ``.aptdata/agents.yaml`` quando o comando
        foi invocado dentro de um projeto (``None`` = não aplicável).
    """
    if explicit is not None:
        if isinstance(explicit, ExecutionMode):
            return explicit
        return ExecutionMode.from_str(explicit)
    return (
        project_default
        or mode_for_command(group, command)
        or ExecutionMode.ONESHOT  # último fallback — nunca retorna None
    )


__all__ = [
    "MODE_DOCS",
    "ModeDoc",
    "ExecutionMode",
    "mode_for_command",
    "resolve_mode",
]
