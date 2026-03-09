"""Rich panel / tree generators for smart-data CLI output."""

from __future__ import annotations

from typing import Any

from rich.panel import Panel
from rich.syntax import Syntax
from rich.tree import Tree


def system_detail_panel(name: str, system_cls: Any) -> Panel:
    """Return a Rich Panel with detailed system information."""
    doc = (system_cls.__doc__ or "No description.").strip()
    module = getattr(system_cls, "__module__", "unknown")
    content = f"[bold]Class:[/bold] {system_cls.__name__}\n[bold]Module:[/bold] {module}\n\n{doc}"
    return Panel(content, title=f"[bold cyan]System: {name}[/bold cyan]", expand=False)


def flow_tree(flow: Any) -> Tree:
    """Return a Rich Tree representing the flow's component DAG."""
    tree = Tree(f"[bold]{getattr(flow, 'flow_id', 'flow')}[/bold]")
    components = getattr(flow, "components", [])
    edges = getattr(flow, "edges", [])

    # Build adjacency for display
    children: dict[str, list[str]] = {}
    for edge in edges:
        src = getattr(edge, "source_id", "?")
        tgt = getattr(edge, "target_id", "?")
        children.setdefault(src, []).append(tgt)

    added: set[str] = set()

    def _add(node: str, branch: Any) -> None:
        if node in added:
            return
        added.add(node)
        b = branch.add(f"[green]{node}[/green]")
        for child in children.get(node, []):
            _add(child, b)

    component_ids = [getattr(c, "component_id", str(i)) for i, c in enumerate(components)]
    all_targets: set[str] = {t for targets in children.values() for t in targets}
    roots = [cid for cid in component_ids if cid not in all_targets]
    if not roots:
        roots = component_ids[:1]

    for root in roots:
        _add(root, tree)

    # Add any unconnected components
    for cid in component_ids:
        if cid not in added:
            tree.add(f"[dim]{cid}[/dim]")

    return tree


def yaml_preview(content: str) -> Syntax:
    """Return a Rich Syntax object for YAML content."""
    return Syntax(content, "yaml", theme="monokai", line_numbers=True)


def component_panel(component: Any) -> Panel:
    """Return a Rich Panel with component metadata."""
    cid = getattr(component, "component_id", "unknown")
    meta = getattr(component, "metadata", None)
    lines = [f"[bold]ID:[/bold] {cid}"]
    if meta is not None:
        kind = getattr(meta, "kind", None)
        if kind is not None:
            lines.append(f"[bold]Kind:[/bold] {kind}")
        tags = getattr(meta, "tags", [])
        if tags:
            lines.append(f"[bold]Tags:[/bold] {', '.join(tags)}")
        desc = getattr(meta, "description", "")
        if desc:
            lines.append(f"[bold]Description:[/bold] {desc}")
    return Panel("\n".join(lines), title=f"[bold cyan]Component: {cid}[/bold cyan]", expand=False)
