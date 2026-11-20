import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

try:
    import pytest
except ImportError:
    class _MockPytest:
        @staticmethod
        def fixture(*args, **kwargs):
            def decorator(f):
                return f
            return decorator
    pytest = _MockPytest()

from src.graph.builder import load_snapshot, build_transit_graph
from src.graph.analytics import simulate_disruption, compute_centrality_metrics


@pytest.fixture(scope="module")
def transit_graph():
    snapshot_path = os.path.join(base_dir, "data", "processed", "graph_snapshot.json")
    csv_path = os.path.join(base_dir, "data", "raw", "lineas-y-horarios.csv")
    if os.path.exists(snapshot_path):
        return load_snapshot(snapshot_path)
    return build_transit_graph(csv_path)


def test_baseline_no_disruption(transit_graph):
    res = simulate_disruption(transit_graph, removed_lines=[], closed_nodes=[])
    assert res["disconnected_pairs_count"] == 0
    assert res["disconnected_pairs_pct"] == 0.0
    assert res["avg_travel_time_increase_pct"] == 0.0
    assert res["baseline_reachable_pairs"] > 0


def test_trunk_line_outage_impact(transit_graph):
    res = simulate_disruption(transit_graph, removed_lines=["015", "010"], closed_nodes=[])
    assert res["baseline_reachable_pairs"] > 0
    assert res["avg_travel_time_increase_pct"] >= 0.0


def test_major_hub_closure_resilience(transit_graph):
    res = simulate_disruption(transit_graph, removed_lines=[], closed_nodes=["INTERCAMBIADOR_SANTA_CRUZ"])
    assert res["disconnected_pairs_count"] > 0
    assert res["disconnected_pairs_pct"] > 0.0


def test_centrality_metrics_structure(transit_graph):
    rankings = compute_centrality_metrics(transit_graph, top_k=5)
    assert len(rankings) == 5
    assert rankings[0]["betweenness_centrality"] > 0
    assert rankings[0]["node_id"] in ["INTERCAMBIADOR_SANTA_CRUZ", "INTERCAMBIADOR_LA_LAGUNA"]


if __name__ == "__main__":
    g = transit_graph()
    test_baseline_no_disruption(g)
    test_trunk_line_outage_impact(g)
    test_major_hub_closure_resilience(g)
    test_centrality_metrics_structure(g)
    print("All resilience tests passed successfully!")
