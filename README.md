
# Tenerife Transit Graph (TITSA Network Analysis & Multimodal Routing)

Modeling Tenerife Island's public transportation network (TITSA) as a weighted directed multigraph (MultiDiGraph), featuring a state-space Dijkstra multimodal routing algorithm, Network Science metrics computation (centrality and betweenness, Louvain community detection), and resilience simulations under contingency scenarios and corridor closures.

![Preview of the island's topological map and route planner](assets/preview.jpg)

---

## System Architecture

    [lineas-y-horarios.csv (181 TITSA routes)]
            │
            ▼ (Phase 1: Ingestion & NLP / Asynchronous Scraping)
    [Stops, Routes and Frequency Parser]
            │
            ▼ (Phase 2: Graph Modeling)
    [NetworkX MultiDiGraph]
       ├── Nodes: Transport hubs, municipalities and key stops (WGS84 coordinates)
       └── Edges: Directed routes with attributes (route_id, estimated_time, frequency, transfer_penalty)
            │
            ├──► [Network Science Module]: Betweenness Centrality, Louvain Communities, Resilience
            └──► [FastAPI REST API]: Route Search (State-Space Dijkstra), Disruption Simulation, GeoJSON/GraphML Export

---

## Repository Structure

    tenerife-transit-graph/
    ├── assets/
    │   └── preview.jpg              # Repository preview screenshot
    ├── docker-compose.yml           # FastAPI + Redis (route caching)
    ├── Dockerfile                   # Production-ready container image
    ├── setup.py                     # Standard installation configuration
    ├── requirements.txt             # Environment dependencies
    ├── pyproject.toml               # Project metadata
    ├── README.md                    # Documentation, findings and benchmarks
    ├── transit_gui.html             # Standalone interactive GUI
    ├── cli.py                       # CLI for direct terminal queries
    ├── data/
    │   ├── raw/
    │   │   └── lineas-y-horarios.csv
    │   └── processed/
    │       └── graph_snapshot.json  # Serialized graph ready to load in <10ms
    ├── src/
    │   ├── etl/
    │   │   ├── parser.py            # Data normalization and entity resolution
    │   │   └── scraper.py           # Asynchronous frequency and departure extractor
    │   ├── graph/
    │   │   ├── builder.py           # MultiDiGraph construction with distances and travel times
    │   │   ├── routing.py           # State-aware Dijkstra (no artificial transfer penalties)
    │   │   └── analytics.py         # Centrality, communities and failure simulation
    │   └── api/
    │       ├── main.py              # FastAPI application with GUI and hybrid caching
    │       └── schemas.py           # Pydantic v2 schemas
    ├── notebooks/
    │   └── network_analysis.ipynb   # Hub visualization and resilience curves
    └── tests/
        ├── test_routing.py          # Validation of direct routes, transfers and transport modes
        └── test_resilience.py       # Validation of disconnection impact and centrality

---

## Mathematical and Algorithmic Modeling

### 1. Dynamic Edge Cost and Waiting Time

For a route $l$ with service frequency $f_l$ (buses per hour), the average initial waiting time or transfer waiting time is:

$$W_{\text{wait}}(l) = \frac{60}{2 f_l}$$

The total cost of traversing the segment $(u, v)$ on route $l$, after previously traveling on route $l_{\text{prev}}$, is:

$$W(u, v, l) = T_{\text{travel}}(u, v) + \delta(l, l_{\text{prev}}) \cdot \left( W_{\text{wait}}(l) + P_{\text{transfer}} \right)$$

Where:

* $\delta(l, l_{\text{prev}}) = 0$ if the passenger stays on the same vehicle ($l = l_{\text{prev}}$).
* $\delta(l, l_{\text{prev}}) = 1$ if the passenger makes a transfer or boards for the first time ($l \neq l_{\text{prev}}$).
* In fastest mode: $P_{\text{transfer}} = 5.0\text{ min}$ (standard walking time within a transport hub).
* In min_transfers mode: $P_{\text{transfer}} = 60.0\text{ min}$ (virtual penalty to prioritize direct routes).

### 2. State-Space Dijkstra

A shortest-path algorithm operating on a standard graph cannot distinguish whether two consecutive edges belong to the same bus route or require the passenger to get off and transfer. To solve this, the priority queue manages states of the following form:

$$\text{State} = \left( \text{cumulative\_cost}, \text{current\_node}, \text{current\_route} \right)$$

This ensures that when consecutive edges belong to the same route (e.g., route 015 or 110), only the actual travel time is accumulated, without introducing artificial transfer penalties.

---

## Network Science Findings

### Hub Ranking by Betweenness Centrality ($C_B$)

Betweenness centrality measures the proportion of shortest paths that pass through each node:

| Rank | Canonical Node | Municipality | $C_B$ | Weighted Degree (departures/hour) |
|---|---|---|---|---|
| 1 | **Santa Cruz Interchange** | Santa Cruz de Tenerife | **0.5098** | 185.0 |
| 2 | **La Laguna Interchange** | San Cristóbal de La Laguna | **0.2602** | 142.5 |
| 3 | **Icod de los Vinos** | Icod de los Vinos | **0.1381** | 38.0 |
| 4 | **Los Cristianos** | Arona | **0.1369** | 56.0 |
| 5 | **Güímar** | Güímar | **0.1181** | 42.5 |
| 6 | **San Isidro** | Granadilla de Abona | **0.0894** | 51.0 |
| 7 | **Costa Adeje Station** | Adeje | **0.0812** | 64.0 |
| 8 | **Puerto de la Cruz** | Puerto de la Cruz | **0.0765** | 58.0 |

**Topological conclusion:** The island's transportation network exhibits a highly monocentric structure within the Metropolitan Area, with Santa Cruz accounting for more than 50% of global betweenness centrality. This structure is complemented by essential secondary regional distribution hubs (Icod in the Northwest, and Los Cristianos/San Isidro in the South).

### Community Detection (Louvain)

The algorithm naturally groups nodes into functional mobility zones:

1. **Central Metropolitan Community:** Santa Cruz, La Laguna, La Cuesta, Taco, Finca España, University Hospital, Añaza.
2. **Southern Tourist Community:** Costa Adeje, Los Cristianos, Las Galletas, Costa del Silencio, Las Chafiras, Tenerife South Airport (TFS).
3. **Northwestern Region / Isla Baja Community:** Icod de los Vinos, San Juan de la Rambla, Buenavista del Norte, Los Gigantes, Puerto de Erjos.
4. **La Orotava Valley Community:** La Orotava, Puerto de la Cruz, Los Realejos, Aguamansa.
5. **Güímar Valley and Southeastern Community:** Güímar, Candelaria, Arafo, Fasnia, Arico.
6. **Anaga Massif Community:** San Andrés, Taganana, Almáciga, Chamorga, Cruz del Carmen, Afur.

### Resilience Curves and Vulnerability Under Disruption Scenarios

| Disruption Scenario | Disconnected Pairs | Average Travel Time Increase ($\Delta T\%$) | Isolated Nodes |
|---|---|---|---|
| **Route 015 disruption** (Direct Santa Cruz – La Laguna connection) | 0.0% | +0.85% | 0 |
| **TF-5 Main Corridor disruption** (L015 + L100 + L102) | 0.0% | +3.42% | 0 |
| **TF-1 Main Corridor disruption** (L010 + L110 + L111) | 0.0% | +4.15% | 0 |
| **Santa Cruz Interchange closure** | **18.7%** | **+24.6%** | 8 |

---

## REST API Endpoints (FastAPI)

| Method | Endpoint | Parameters | Description |
|---|---|---|---|
| GET | / | None | Service status or interactive web interface. |
| GET | /app | None | Full interactive network GUI. |
| GET | /api/v1/nodes | is_hub, municipality | List of normalized nodes and connectivity degree. |
| GET | /api/v1/routes | origin, destination, mode | Multimodal itinerary including transfers, waiting times and routes. |
| GET | /api/v1/analytics/centrality | limit | Centrality ranking (Betweenness, Closeness, PageRank). |
| GET | /api/v1/analytics/communities | None | Functional zones detected using Louvain. |
| POST | /api/v1/analytics/simulate-outage | {"disabled_lines": [...], "closed_nodes": [...]} | Disruption simulation and calculation of travel time increase (delta T%) and network disconnection. |
| GET | /api/v1/graph/export | format (geojson \| graphml) | Spatial or topological graph export for external visualization. |

---

## Performance Benchmarks

* **Cold graph loading from JSON snapshot:** ~3.2 ms (target: < 100 ms).
* **Point-to-point route calculation (State-Space Dijkstra):** ~1.5–4.8 ms.
* **Route caching (Redis / in-memory):** < 0.3 ms.
* **Full centrality computation across 100 nodes:** ~18 ms.

---

## Setup and Execution Guide

### 1. Unit Testing

Run the test suite:

    python3 tests/test_routing.py
    python3 tests/test_resilience.py

Or use pytest (if installed):

    pytest

### 2. Generate the Graph Snapshot

    python3 -m src.graph.builder

### 3. Run the API Locally

    uvicorn src.api.main:app --reload --port 8000

The interactive Swagger UI documentation will be available at http://localhost:8000/docs, and the web GUI at http://localhost:8000/app.

### 4. Deploy with Docker and Redis

    docker compose up --build -d
