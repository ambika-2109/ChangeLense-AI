"""Deterministic dependency graph construction and downstream impact traversal."""

from __future__ import annotations

import networkx as nx

from changelens.schemas.report import ResourceChange


def build_graph(
    changes: list[ResourceChange],
    dependencies: dict[str, list[str]] | None = None,
) -> nx.DiGraph:
    """Build dependency-to-dependent edges from plan and configuration metadata."""
    graph = nx.DiGraph()
    for change in changes:
        graph.add_node(change.address)
    edges = dict(dependencies or {})
    for change in changes:
        edges.setdefault(change.address, change.depends_on)
    for address, required in edges.items():
        graph.add_node(address)
        for dependency in required:
            graph.add_node(dependency)
            graph.add_edge(dependency, address)
    return graph


def downstream_impact(graph: nx.DiGraph, addresses: list[str]) -> list[str]:
    """Return changed roots and all transitive dependents, in stable order."""
    affected: set[str] = set()
    for address in addresses:
        if address not in graph:
            affected.add(address)
            continue
        affected.add(address)
        affected.update(nx.descendants(graph, address))
    return sorted(affected)
