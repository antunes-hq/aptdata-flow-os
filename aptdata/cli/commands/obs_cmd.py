"""CLI sub-commands for the aptdata observability trace (``aptdata obs``).

Projeção operável do event store (Observer/ObservabilityStore): resumo
agregado e tail dos últimos eventos, ambos com ``--json``.
"""

from __future__ import annotations

import json
from datetime import datetime

import typer

from aptdata.cli.rendering.console import SmartConsole

obs_app = typer.Typer(
    name="obs", help="Inspect the aptdata observability trace (event store)."
)


@obs_app.command("summary")
def obs_summary(
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """Aggregated view: events by kind, routing modes, dispatch health."""
    from aptdata.observability import Observer  # noqa: PLC0415

    console = SmartConsole(json_mode=json_mode)
    summary = Observer.get().summary()

    if json_mode:
        print(json.dumps(summary, ensure_ascii=False), flush=True)
        return

    console.print(
        f"[bold]events:[/bold] {summary['total_events']}"
        f"  [dim]({summary['db']})[/dim]"
    )
    for kind, count in sorted(summary["by_kind"].items()):
        console.print(f"  {kind}: {count}")
    modes = summary["decisions_by_mode"]
    if modes:
        rendered = ", ".join(f"{m}={c}" for m, c in sorted(modes.items()))
        console.print(f"[bold]decisions:[/bold] {rendered}")
    d = summary["dispatches"]
    if d["total"]:
        latency = f", avg {d['avg_latency_ms']}ms" if d["avg_latency_ms"] else ""
        console.print(f"[bold]dispatches:[/bold] {d['ok']}/{d['total']} ok{latency}")


@obs_app.command("tail")
def obs_tail(
    limit: int = typer.Option(20, "--limit", "-n", help="Max events to show."),
    kind: str = typer.Option(None, "--kind", "-k", help="Filter by event kind."),
    run_id: str = typer.Option(None, "--run-id", help="Filter by run_id."),
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """Show the latest trace events (routing decisions, dispatches, ...)."""
    from aptdata.observability import Observer  # noqa: PLC0415

    console = SmartConsole(json_mode=json_mode)
    events = Observer.get().tail(limit, kind=kind, run_id=run_id)

    if json_mode:
        print(
            json.dumps({"events": events, "count": len(events)}, ensure_ascii=False),
            flush=True,
        )
        return

    if not events:
        console.warning("No events recorded yet.")
        return
    for e in events:
        when = datetime.fromtimestamp(e["ts"]).strftime("%H:%M:%S")
        agent = f" [{e['agent_id']}]" if e["agent_id"] else ""
        run = f" run={e['run_id']}" if e["run_id"] else ""
        payload = json.dumps(e["payload"], ensure_ascii=False)
        console.print(f"{when}  {e['kind']}{agent}{run}  {payload}")
