from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class NodeItem(BaseModel):
    id: str
    name: str
    municipality: str
    lat: float
    lon: float
    is_hub: bool
    degree: int
    in_degree: int
    out_degree: int


class NodesListResponse(BaseModel):
    total: int
    nodes: List[NodeItem]


class RouteStepItem(BaseModel):
    from_node: str
    to_node: str
    line_id: str
    line_name: str
    travel_time: float
    wait_time: float
    is_transfer: bool


class RouteResponse(BaseModel):
    origin: str
    destination: str
    mode: str
    found: bool
    total_time_minutes: Optional[float] = None
    travel_time_minutes: Optional[float] = None
    wait_time_minutes: Optional[float] = None
    transfers_count: Optional[int] = None
    score_cost: Optional[float] = None
    legs: List[RouteStepItem] = Field(default_factory=list)
    lines_used: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class CentralityItem(BaseModel):
    node_id: str
    name: str
    municipality: str
    is_hub: bool
    betweenness_centrality: float
    closeness_centrality: float
    pagerank: float
    in_degree: int
    out_degree: int
    total_degree: int
    weighted_degree: float


class CentralityResponse(BaseModel):
    total: int
    rankings: List[CentralityItem]


class DisruptionRequest(BaseModel):
    disabled_lines: Optional[List[Any]] = Field(default_factory=list)
    closed_nodes: Optional[List[str]] = Field(default_factory=list)


class DisruptionResponse(BaseModel):
    disabled_lines: List[str]
    closed_nodes: List[str]
    baseline_reachable_pairs: int
    disrupted_reachable_pairs: int
    disconnected_pairs_count: int
    disconnected_pairs_pct: float
    avg_travel_time_increase_pct: float
    isolated_nodes_count: int
    isolated_nodes: List[str]
