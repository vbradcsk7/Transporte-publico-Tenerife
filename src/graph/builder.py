import os
import json
import math
import networkx as nx
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from src.etl.parser import NODE_REGISTRY, parse_csv_routes
from src.etl.scraper import get_default_frequency


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def estimate_travel_time(line_number: str, line_name: str, distance_km: float) -> float:
    name_upper = line_name.upper()
    num_str = str(line_number).lstrip("0")
    try:
        num = int(num_str) if num_str else 0
    except ValueError:
        num = 0

    if any(k in name_upper for k in ["DIRECTA", "DIRECTO", "SIN PARADAS"]) or num in [10, 15, 100, 103, 110, 112, 477]:
        speed_kmh = 65.0
        dwell_min = 1.5
    elif any(k in name_upper for k in ["TEIDE", "PORTILLO", "MASCA", "TENO", "CHAMORGA", "AFUR", "ALMACIGA"]):
        speed_kmh = 25.0
        dwell_min = 2.0
    elif 900 <= num <= 999 or 200 <= num <= 299:
        speed_kmh = 22.0
        dwell_min = 2.5
    else:
        speed_kmh = 40.0
        dwell_min = 2.0

    travel_min = (distance_km / speed_kmh) * 60.0 + dwell_min
    return max(3.0, round(travel_min, 1))


def build_transit_graph(csv_path: str, frequency_map: Optional[Dict[str, float]] = None) -> nx.MultiDiGraph:
    routes = parse_csv_routes(csv_path)
    g = nx.MultiDiGraph()

    for node_id, data in NODE_REGISTRY.items():
        g.add_node(
            node_id,
            id=node_id,
            name=data["name"],
            municipality=data["municipality"],
            lat=data["lat"],
            lon=data["lon"],
            is_hub=data["is_hub"]
        )

    for route in routes:
        line_num = route["line_number"]
        line_name = route["line_name"]
        stops = route["stops"]
        is_circular = route["is_circular"]

        freq = frequency_map.get(line_num) if frequency_map else None
        if freq is None:
            freq = get_default_frequency(line_num, line_name)

        wait_time = round(60.0 / (2.0 * max(0.1, freq)), 1)

        trajectories = [stops]
        if not is_circular:
            trajectories.append(list(reversed(stops)))

        for traj in trajectories:
            for i in range(len(traj) - 1):
                u = traj[i]
                v = traj[i + 1]
                if u == v or u not in g or v not in g:
                    continue

                u_data = g.nodes[u]
                v_data = g.nodes[v]
                dist_km = round(haversine_distance_km(u_data["lat"], u_data["lon"], v_data["lat"], v_data["lon"]), 2)
                t_est = estimate_travel_time(line_num, line_name, dist_km)

                g.add_edge(
                    u,
                    v,
                    linea_id=line_num,
                    linea_nombre=line_name,
                    tiempo_est=t_est,
                    distancia_km=dist_km,
                    frecuencia=freq,
                    wait_time=wait_time,
                    penalizacion_transbordo=5.0
                )

    return g


def export_snapshot(graph: nx.MultiDiGraph, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    nodes_data = []
    for node_id, data in graph.nodes(data=True):
        nodes_data.append({
            "id": node_id,
            "name": data.get("name", node_id),
            "municipality": data.get("municipality", ""),
            "lat": data.get("lat", 0.0),
            "lon": data.get("lon", 0.0),
            "is_hub": data.get("is_hub", False)
        })

    edges_data = []
    lines_set = set()
    for u, v, k, data in graph.edges(keys=True, data=True):
        lines_set.add(data.get("linea_id", ""))
        edges_data.append({
            "u": u,
            "v": v,
            "key": k,
            "linea_id": data.get("linea_id", ""),
            "linea_nombre": data.get("linea_nombre", ""),
            "tiempo_est": data.get("tiempo_est", 10.0),
            "distancia_km": data.get("distancia_km", 5.0),
            "frecuencia": data.get("frecuencia", 1.0),
            "wait_time": data.get("wait_time", 30.0),
            "penalizacion_transbordo": data.get("penalizacion_transbordo", 5.0)
        })

    snapshot = {
        "metadata": {
            "total_nodes": len(nodes_data),
            "total_edges": len(edges_data),
            "total_lines": len(lines_set),
            "generated_at": datetime.utcnow().isoformat() + "Z"
        },
        "nodes": nodes_data,
        "edges": edges_data
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)


def load_snapshot(snapshot_path: str) -> nx.MultiDiGraph:
    with open(snapshot_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    g = nx.MultiDiGraph()
    for n in data.get("nodes", []):
        g.add_node(
            n["id"],
            id=n["id"],
            name=n["name"],
            municipality=n["municipality"],
            lat=n["lat"],
            lon=n["lon"],
            is_hub=n["is_hub"]
        )

    for e in data.get("edges", []):
        g.add_edge(
            e["u"],
            e["v"],
            key=e.get("key"),
            linea_id=e["linea_id"],
            linea_nombre=e["linea_nombre"],
            tiempo_est=float(e["tiempo_est"]),
            distancia_km=float(e["distancia_km"]),
            frecuencia=float(e["frecuencia"]),
            wait_time=float(e["wait_time"]),
            penalizacion_transbordo=float(e.get("penalizacion_transbordo", 5.0))
        )

    return g


def graph_to_geojson(graph: nx.MultiDiGraph) -> Dict[str, Any]:
    features = []

    for node_id, data in graph.nodes(data=True):
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [data["lon"], data["lat"]]
            },
            "properties": {
                "id": node_id,
                "name": data["name"],
                "municipality": data["municipality"],
                "is_hub": data["is_hub"],
                "degree": graph.degree(node_id)
            }
        })

    for u, v, k, data in graph.edges(keys=True, data=True):
        u_data = graph.nodes[u]
        v_data = graph.nodes[v]
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [u_data["lon"], u_data["lat"]],
                    [v_data["lon"], v_data["lat"]]
                ]
            },
            "properties": {
                "from": u,
                "to": v,
                "key": k,
                "linea_id": data["linea_id"],
                "linea_nombre": data["linea_nombre"],
                "tiempo_est": data["tiempo_est"],
                "distancia_km": data["distancia_km"],
                "frecuencia": data["frecuencia"],
                "wait_time": data["wait_time"]
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }


def graph_to_graphml(graph: nx.MultiDiGraph) -> str:
    simple_g = nx.DiGraph()
    for n, data in graph.nodes(data=True):
        simple_g.add_node(n, label=data.get("name", n), municipality=data.get("municipality", ""))

    for u, v, data in graph.edges(data=True):
        if not simple_g.has_edge(u, v):
            simple_g.add_edge(u, v, weight=data.get("tiempo_est", 10.0), linea_id=data.get("linea_id", ""))

    return "\n".join(nx.generate_graphml(simple_g))


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    csv_file = os.path.join(base_dir, "data", "raw", "lineas-y-horarios.csv")
    out_file = os.path.join(base_dir, "data", "processed", "graph_snapshot.json")
    network = build_transit_graph(csv_file)
    export_snapshot(network, out_file)
    print(f"Graph snapshot created: {network.number_of_nodes()} nodes, {network.number_of_edges()} edges")
