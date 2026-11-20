import heapq
from typing import Dict, Any, List, Optional, Tuple
import networkx as nx
from src.etl.parser import resolve_entity


def find_optimal_route(
    graph: nx.MultiDiGraph,
    origin: str,
    destination: str,
    mode: str = "fastest",
    transfer_penalty_override: Optional[float] = None,
    max_transfers: int = 4
) -> Dict[str, Any]:
    orig_canonical = origin if origin in graph else resolve_entity(origin)
    dest_canonical = destination if destination in graph else resolve_entity(destination)

    if not orig_canonical or orig_canonical not in graph:
        return {
            "origin": origin,
            "destination": destination,
            "found": False,
            "error": f"Origin node '{origin}' could not be resolved in transit network"
        }

    if not dest_canonical or dest_canonical not in graph:
        return {
            "origin": origin,
            "destination": destination,
            "found": False,
            "error": f"Destination node '{destination}' could not be resolved in transit network"
        }

    if orig_canonical == dest_canonical:
        return {
            "origin": orig_canonical,
            "destination": dest_canonical,
            "mode": mode,
            "found": True,
            "total_time_minutes": 0.0,
            "travel_time_minutes": 0.0,
            "wait_time_minutes": 0.0,
            "transfers_count": 0,
            "legs": [],
            "lines_used": []
        }

    penalty_weight = transfer_penalty_override
    if penalty_weight is None:
        penalty_weight = 60.0 if mode == "min_transfers" else 5.0

    pq = []
    heapq.heappush(pq, (0.0, 0.0, 0.0, orig_canonical, None, 0, []))
    best_cost: Dict[Tuple[str, Optional[str]], float] = {}

    while pq:
        eff_cost, trav_time, wait_time, u, curr_line, transfers, steps = heapq.heappop(pq)

        if u == dest_canonical:
            real_walk_transfer_time = transfers * 5.0
            total_real_time = trav_time + wait_time + real_walk_transfer_time
            lines_used = []
            for s in steps:
                if s["line_id"] not in lines_used:
                    lines_used.append(s["line_id"])

            return {
                "origin": orig_canonical,
                "destination": dest_canonical,
                "mode": mode,
                "found": True,
                "total_time_minutes": round(total_real_time, 1),
                "travel_time_minutes": round(trav_time, 1),
                "wait_time_minutes": round(wait_time, 1),
                "transfers_count": transfers,
                "score_cost": round(eff_cost, 1),
                "legs": steps,
                "lines_used": lines_used
            }

        state_key = (u, curr_line)
        if eff_cost > best_cost.get(state_key, float("inf")):
            continue

        for _, v, data in graph.out_edges(u, data=True):
            edge_line = data["linea_id"]
            edge_name = data.get("linea_nombre", "")
            t_edge = data["tiempo_est"]
            w_edge = data["wait_time"]

            if curr_line is None:
                leg_wait = w_edge
                leg_penalty = 0.0
                is_trans = False
                new_trans = 0
            elif curr_line == edge_line:
                leg_wait = 0.0
                leg_penalty = 0.0
                is_trans = False
                new_trans = transfers
            else:
                leg_wait = w_edge
                leg_penalty = penalty_weight
                is_trans = True
                new_trans = transfers + 1

            if new_trans > max_transfers:
                continue

            step_entry = {
                "from_node": u,
                "to_node": v,
                "line_id": edge_line,
                "line_name": edge_name,
                "travel_time": t_edge,
                "wait_time": leg_wait,
                "is_transfer": is_trans
            }

            next_eff_cost = eff_cost + t_edge + leg_wait + leg_penalty
            next_trav = trav_time + t_edge
            next_wait = wait_time + leg_wait
            next_state_key = (v, edge_line)

            if next_eff_cost < best_cost.get(next_state_key, float("inf")):
                best_cost[next_state_key] = next_eff_cost
                new_steps = list(steps)
                new_steps.append(step_entry)
                heapq.heappush(pq, (
                    next_eff_cost,
                    next_trav,
                    next_wait,
                    v,
                    edge_line,
                    new_trans,
                    new_steps
                ))

    return {
        "origin": orig_canonical,
        "destination": dest_canonical,
        "mode": mode,
        "found": False,
        "error": "No transit path found within transfer limits"
    }
