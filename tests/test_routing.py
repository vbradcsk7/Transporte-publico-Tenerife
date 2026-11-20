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
from src.graph.routing import find_optimal_route


@pytest.fixture(scope="module")
def transit_graph():
    snapshot_path = os.path.join(base_dir, "data", "processed", "graph_snapshot.json")
    csv_path = os.path.join(base_dir, "data", "raw", "lineas-y-horarios.csv")
    if os.path.exists(snapshot_path):
        return load_snapshot(snapshot_path)
    return build_transit_graph(csv_path)


def test_direct_route_between_metropolitan_hubs(transit_graph):
    res = find_optimal_route(
        transit_graph,
        origin="INTERCAMBIADOR_SANTA_CRUZ",
        destination="INTERCAMBIADOR_LA_LAGUNA",
        mode="fastest"
    )
    assert res["found"] is True
    assert res["transfers_count"] == 0
    assert len(res["legs"]) >= 1
    assert res["total_time_minutes"] > 0
    assert "015" in res["lines_used"] or "014" in res["lines_used"]


def test_same_origin_and_destination(transit_graph):
    res = find_optimal_route(
        transit_graph,
        origin="INTERCAMBIADOR_SANTA_CRUZ",
        destination="INTERCAMBIADOR_SANTA_CRUZ",
        mode="fastest"
    )
    assert res["found"] is True
    assert res["total_time_minutes"] == 0.0
    assert res["transfers_count"] == 0
    assert len(res["legs"]) == 0


def test_transfer_route_north_to_south(transit_graph):
    res = find_optimal_route(
        transit_graph,
        origin="TACORONTE",
        destination="AEROPUERTO_SUR_TFS",
        mode="fastest"
    )
    assert res["found"] is True
    assert res["transfers_count"] >= 1
    assert len(res["legs"]) >= 2
    assert res["total_time_minutes"] > res["travel_time_minutes"]


def test_min_transfers_mode_penalization(transit_graph):
    res_fast = find_optimal_route(
        transit_graph,
        origin="TACORONTE",
        destination="AEROPUERTO_SUR_TFS",
        mode="fastest"
    )
    res_min_transfers = find_optimal_route(
        transit_graph,
        origin="TACORONTE",
        destination="AEROPUERTO_SUR_TFS",
        mode="min_transfers"
    )
    assert res_fast["found"] is True
    assert res_min_transfers["found"] is True
    assert res_min_transfers["transfers_count"] <= res_fast["transfers_count"]


def test_nonexistent_node_resolution(transit_graph):
    res = find_optimal_route(
        transit_graph,
        origin="NONEXISTENT_STATION_XYZ",
        destination="INTERCAMBIADOR_SANTA_CRUZ",
        mode="fastest"
    )
    assert res["found"] is False
    assert "error" in res


if __name__ == "__main__":
    g = transit_graph()
    test_direct_route_between_metropolitan_hubs(g)
    test_same_origin_and_destination(g)
    test_transfer_route_north_to_south(g)
    test_min_transfers_mode_penalization(g)
    test_nonexistent_node_resolution(g)
    print("All routing tests passed successfully!")
