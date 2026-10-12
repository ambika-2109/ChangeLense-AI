from changelens.dependency_graph.impact import build_graph, downstream_impact
from changelens.schemas.report import ResourceChange


def make_change(address: str, dependencies: list[str]) -> ResourceChange:
    return ResourceChange(
        address=address,
        resource_type="test_resource",
        actions=["update"],
        operation="update",
        depends_on=dependencies,
        evidence_ref="plan.json#/resource_changes/0",
    )


def test_graph_walks_transitive_dependencies_and_tolerates_cycles() -> None:
    changes = [
        make_change("db", []),
        make_change("api", ["db"]),
        make_change("worker", ["api"]),
        make_change("db", ["worker"]),
    ]
    graph = build_graph(changes)
    assert downstream_impact(graph, ["db"]) == ["api", "db", "worker"]


def test_unrelated_resources_are_not_in_impact() -> None:
    graph = build_graph([make_change("db", []), make_change("cache", [])])
    assert downstream_impact(graph, ["db"]) == ["db"]
