import os
import json
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Query, Response, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import networkx as nx

from src.api.schemas import (
    NodeItem,
    NodesListResponse,
    RouteResponse,
    CentralityResponse,
    CentralityItem,
    DisruptionRequest,
    DisruptionResponse,
)
from src.graph.builder import (
    load_snapshot,
    build_transit_graph,
    export_snapshot,
    graph_to_geojson,
    graph_to_graphml,
)
from src.graph.routing import find_optimal_route
from src.graph.analytics import (
    compute_centrality_metrics,
    simulate_disruption,
    detect_communities,
)


class SimpleCache:
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = None
        self.memory_cache: Dict[str, Any] = {}
        if redis_url:
            try:
                import redis
                client = redis.Redis.from_url(redis_url, decode_responses=True)
                client.ping()
                self.redis_client = client
            except Exception:
                self.redis_client = None

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if self.redis_client:
            try:
                val = self.redis_client.get(key)
                if val:
                    return json.loads(val)
            except Exception:
                pass
        return self.memory_cache.get(key)

    def set(self, key: str, value: Dict[str, Any], ttl_seconds: int = 3600) -> None:
        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl_seconds, json.dumps(value))
                return
            except Exception:
                pass
        self.memory_cache[key] = value


graph_instance: Optional[nx.MultiDiGraph] = None
cache_instance: Optional[SimpleCache] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph_instance, cache_instance

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    snapshot_path = os.getenv("SNAPSHOT_PATH", os.path.join(base_dir, "data", "processed", "graph_snapshot.json"))
    csv_path = os.getenv("CSV_PATH", os.path.join(base_dir, "data", "raw", "lineas-y-horarios.csv"))
    redis_url = os.getenv("REDIS_URL", None)

    if os.path.exists(snapshot_path):
        graph_instance = load_snapshot(snapshot_path)
    else:
        graph_instance = build_transit_graph(csv_path)
        export_snapshot(graph_instance, snapshot_path)

    cache_instance = SimpleCache(redis_url)
    yield


app = FastAPI(
    title="Tenerife Transit Graph API",
    description="Multimodal state-space routing and complex network analytics for TITSA public transit in Tenerife",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
def get_root_or_gui(request: Request):
    accept = request.headers.get("accept", "")
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    gui_file = os.path.join(base_dir, "transit_gui.html")

    if "text/html" in accept and os.path.exists(gui_file):
        with open(gui_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())

    global graph_instance
    nodes_cnt = graph_instance.number_of_nodes() if graph_instance else 0
    edges_cnt = graph_instance.number_of_edges() if graph_instance else 0
    data = {
        "status": "online",
        "service": "Tenerife Transit Graph API",
        "version": "1.0.0",
        "total_nodes": nodes_cnt,
        "total_edges": edges_cnt,
        "interactive_gui": "/app",
        "documentation": "/docs"
    }
    return Response(content=json.dumps(data, indent=2), media_type="application/json")


@app.get("/app", response_class=HTMLResponse)
def get_interactive_gui():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    gui_file = os.path.join(base_dir, "transit_gui.html")
    if os.path.exists(gui_file):
        with open(gui_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>GUI not found</h1>", status_code=404)


@app.get("/api/v1/nodes", response_model=NodesListResponse)
def list_nodes(
    is_hub: Optional[bool] = Query(None, description="Filter hubs only"),
    municipality: Optional[str] = Query(None, description="Filter by municipality")
):
    global graph_instance
    if not graph_instance:
        raise HTTPException(status_code=503, detail="Graph not initialized")

    result = []
    for node_id, data in graph_instance.nodes(data=True):
        if is_hub is not None and data.get("is_hub", False) != is_hub:
            continue
        if municipality and municipality.lower() not in data.get("municipality", "").lower():
            continue

        deg_in = graph_instance.in_degree(node_id)
        deg_out = graph_instance.out_degree(node_id)
        result.append(NodeItem(
            id=node_id,
            name=data.get("name", node_id),
            municipality=data.get("municipality", ""),
            lat=data.get("lat", 0.0),
            lon=data.get("lon", 0.0),
            is_hub=data.get("is_hub", False),
            degree=deg_in + deg_out,
            in_degree=deg_in,
            out_degree=deg_out
        ))

    return NodesListResponse(total=len(result), nodes=result)


@app.get("/api/v1/routes", response_model=RouteResponse)
def compute_route(
    origin: str = Query(..., description="Origin node name or ID"),
    destination: str = Query(..., description="Destination node name or ID"),
    mode: str = Query("fastest", regex="^(fastest|min_transfers)$", description="Optimization mode")
):
    global graph_instance, cache_instance
    if not graph_instance:
        raise HTTPException(status_code=503, detail="Graph not initialized")

    cache_key = f"route:{origin.strip().upper()}:{destination.strip().upper()}:{mode}"
    if cache_instance:
        cached = cache_instance.get(cache_key)
        if cached:
            return cached

    res = find_optimal_route(graph_instance, origin, destination, mode=mode)
    if not res.get("found"):
        raise HTTPException(status_code=404, detail=res.get("error", "No route found"))

    if cache_instance:
        cache_instance.set(cache_key, res)

    return res


@app.get("/api/v1/analytics/centrality", response_model=CentralityResponse)
def get_centrality_rankings(
    limit: int = Query(15, ge=1, le=100, description="Top K nodes to return")
):
    global graph_instance
    if not graph_instance:
        raise HTTPException(status_code=503, detail="Graph not initialized")

    rankings_raw = compute_centrality_metrics(graph_instance, top_k=limit)
    items = [CentralityItem(**item) for item in rankings_raw]
    return CentralityResponse(total=len(items), rankings=items)


@app.get("/api/v1/analytics/communities")
def get_network_communities():
    global graph_instance
    if not graph_instance:
        raise HTTPException(status_code=503, detail="Graph not initialized")

    comms = detect_communities(graph_instance)
    return {"total_communities": len(comms), "communities": comms}


@app.post("/api/v1/analytics/simulate-outage", response_model=DisruptionResponse)
def post_simulate_outage(payload: DisruptionRequest):
    global graph_instance
    if not graph_instance:
        raise HTTPException(status_code=503, detail="Graph not initialized")

    str_lines = [str(x) for x in (payload.disabled_lines or [])]
    res = simulate_disruption(graph_instance, removed_lines=str_lines, closed_nodes=payload.closed_nodes)
    return DisruptionResponse(**res)


@app.get("/api/v1/graph/export")
def export_graph_data(
    format: str = Query("geojson", regex="^(geojson|graphml)$", description="Export format")
):
    global graph_instance
    if not graph_instance:
        raise HTTPException(status_code=503, detail="Graph not initialized")

    if format == "geojson":
        return graph_to_geojson(graph_instance)
    elif format == "graphml":
        xml_content = graph_to_graphml(graph_instance)
        return Response(content=xml_content, media_type="application/xml")
