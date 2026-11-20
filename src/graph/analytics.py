import statistics
from typing import Dict, Any, List, Optional, Tuple, Set
import networkx as nx


def collapse_to_simple_digraph(graph: nx.MultiDiGraph) -> nx.DiGraph:
    dg = nx.DiGraph()
    for n, data in graph.nodes(data=True):
        dg.add_node(n, **data)

    for u, v, data in graph.edges(data=True):
        t_est = data.get("tiempo_est", 10.0)
        freq = data.get("frecuencia", 1.0)
        if dg.has_edge(u, v):
            curr = dg[u][v]
            curr["weight"] = min(curr["weight"], t_est)
            curr["frequency"] += freq
        else:
            dg.add_edge(u, v, weight=t_est, frequency=freq)

    return dg


def compute_centrality_metrics(graph: nx.MultiDiGraph, top_k: int = 15) -> List[Dict[str, Any]]:
    simple_g = collapse_to_simple_digraph(graph)

    bc = nx.betweenness_centrality(simple_g, weight="weight", normalized=True)
    cc = nx.closeness_centrality(simple_g, distance="weight")
    try:
        pr = nx.pagerank(simple_g, weight="frequency", alpha=0.85)
    except Exception:
        pr = {n: 0.0 for n in simple_g.nodes()}

    weighted_degrees: Dict[str, float] = {}
    for n in graph.nodes():
        w_in = sum(data.get("frecuencia", 1.0) for _, _, data in graph.in_edges(n, data=True))
        w_out = sum(data.get("frecuencia", 1.0) for _, _, data in graph.out_edges(n, data=True))
        weighted_degrees[n] = round(w_in + w_out, 2)

    rankings = []
    for node_id, data in graph.nodes(data=True):
        deg_in = graph.in_degree(node_id)
        deg_out = graph.out_degree(node_id)
        rankings.append({
            "node_id": node_id,
            "name": data.get("name", node_id),
            "municipality": data.get("municipality", ""),
            "is_hub": data.get("is_hub", False),
            "betweenness_centrality": round(bc.get(node_id, 0.0), 6),
            "closeness_centrality": round(cc.get(node_id, 0.0), 6),
            "pagerank": round(pr.get(node_id, 0.0), 6),
            "in_degree": deg_in,
            "out_degree": deg_out,
            "total_degree": deg_in + deg_out,
            "weighted_degree": weighted_degrees.get(node_id, 0.0)
        })

    rankings.sort(key=lambda x: x["betweenness_centrality"], reverse=True)
    return rankings[:top_k] if top_k else rankings


def detect_communities(graph: nx.MultiDiGraph) -> List[Dict[str, Any]]:
    ug = nx.Graph()
    for u, v, data in graph.edges(data=True):
        freq = data.get("frecuencia", 1.0)
        if ug.has_edge(u, v):
            ug[u][v]["weight"] += freq
        else:
            ug.add_edge(u, v, weight=freq)

    for n in graph.nodes():
        if n not in ug:
            ug.add_node(n)

    try:
        raw_comms = nx.community.louvain_communities(ug, weight="weight", seed=42)
    except Exception:
        raw_comms = [set(c) for c in nx.connected_components(ug)]

    labeled_communities = []
    for idx, c_nodes in enumerate(sorted(raw_comms, key=len, reverse=True)):
        hub_node = None
        for nid in sorted(c_nodes, key=lambda n: graph.degree(n), reverse=True):
            if graph.nodes[nid].get("is_hub", False):
                hub_node = graph.nodes[nid].get("name", nid)
                break
        if not hub_node and c_nodes:
            top_n = max(c_nodes, key=lambda n: graph.degree(n))
            hub_node = graph.nodes[top_n].get("name", top_n)

        labeled_communities.append({
            "community_id": idx + 1,
            "label": f"Zona {hub_node}" if hub_node else f"Comunidad {idx + 1}",
            "size": len(c_nodes),
            "nodes": sorted(list(c_nodes))
        })

    return labeled_communities


def simulate_disruption(
    graph: nx.MultiDiGraph,
    removed_lines: Optional[List[str]] = None,
    closed_nodes: Optional[List[str]] = None
) -> Dict[str, Any]:
    lines_to_remove = set(str(l).zfill(3) for l in (removed_lines or []))
    nodes_to_close = set(closed_nodes or [])

    baseline_simple = collapse_to_simple_digraph(graph)
    all_nodes = [n for n in baseline_simple.nodes() if baseline_simple.degree(n) > 0]

    baseline_paths = dict(nx.all_pairs_dijkstra_path_length(baseline_simple, weight="weight"))
    base_reachable_pairs = 0
    base_times = {}

    for u in all_nodes:
        for v in all_nodes:
            if u != v and v in baseline_paths.get(u, {}):
                base_reachable_pairs += 1
                base_times[(u, v)] = baseline_paths[u][v]

    disrupted_g = graph.copy()

    edges_to_del = []
    for u, v, k, data in disrupted_g.edges(keys=True, data=True):
        if data.get("linea_id") in lines_to_remove:
            edges_to_del.append((u, v, k))

    for u, v, k in edges_to_del:
        if disrupted_g.has_edge(u, v, key=k):
            disrupted_g.remove_edge(u, v, key=k)

    for n in nodes_to_close:
        if disrupted_g.has_node(n):
            disrupted_g.remove_node(n)

    disrupted_simple = collapse_to_simple_digraph(disrupted_g)
    disrupted_paths = dict(nx.all_pairs_dijkstra_path_length(disrupted_simple, weight="weight"))

    disrupted_reachable_pairs = 0
    delays = []

    for u, v in base_times.keys():
        if u in disrupted_simple and v in disrupted_paths.get(u, {}):
            disrupted_reachable_pairs += 1
            t_orig = base_times[(u, v)]
            t_new = disrupted_paths[u][v]
            if t_orig > 0:
                delays.append(((t_new - t_orig) / t_orig) * 100.0)

    disconnected_count = base_reachable_pairs - disrupted_reachable_pairs
    disconnected_pct = round((disconnected_count / max(1, base_reachable_pairs)) * 100.0, 2)
    avg_delay_pct = round(statistics.mean(delays), 2) if delays else 0.0

    newly_isolated = []
    for n in all_nodes:
        if n not in nodes_to_close:
            if n not in disrupted_simple or disrupted_simple.degree(n) == 0:
                newly_isolated.append(n)

    return {
        "disabled_lines": sorted(list(lines_to_remove)),
        "closed_nodes": sorted(list(nodes_to_close)),
        "baseline_reachable_pairs": base_reachable_pairs,
        "disrupted_reachable_pairs": disrupted_reachable_pairs,
        "disconnected_pairs_count": disconnected_count,
        "disconnected_pairs_pct": disconnected_pct,
        "avg_travel_time_increase_pct": avg_delay_pct,
        "isolated_nodes_count": len(newly_isolated),
        "isolated_nodes": newly_isolated
    }
