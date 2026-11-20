import sys
import json
import argparse
from src.graph.builder import load_snapshot
from src.graph.routing import find_optimal_route
from src.graph.analytics import compute_centrality_metrics, simulate_disruption, detect_communities


def main():
    parser = argparse.ArgumentParser(description="Tenerife Transit Graph CLI")
    subparsers = parser.add_subparsers(dest="command")

    route_parser = subparsers.add_parser("route")
    route_parser.add_argument("origin", type=str)
    route_parser.add_argument("destination", type=str)
    route_parser.add_argument("--mode", type=str, default="fastest", choices=["fastest", "min_transfers"])

    centrality_parser = subparsers.add_parser("centrality")
    centrality_parser.add_argument("--top", type=int, default=10)

    disruption_parser = subparsers.add_parser("disruption")
    disruption_parser.add_argument("--lines", nargs="*", default=[])
    disruption_parser.add_argument("--nodes", nargs="*", default=[])

    subparsers.add_parser("communities")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    graph = load_snapshot("data/processed/graph_snapshot.json")

    if args.command == "route":
        res = find_optimal_route(graph, args.origin, args.destination, mode=args.mode)
        print(json.dumps(res, indent=2, ensure_ascii=False))

    elif args.command == "centrality":
        res = compute_centrality_metrics(graph, top_k=args.top)
        print(f"\n{'HUB':<32} {'CB':<10} {'GRADO PONDERADO'}")
        print("-" * 55)
        for item in res:
            print(f"{item['name']:<32} {item['betweenness_centrality']:<10.4f} {item['weighted_degree']}")

    elif args.command == "disruption":
        res = simulate_disruption(graph, removed_lines=args.lines, closed_nodes=args.nodes)
        print(json.dumps(res, indent=2, ensure_ascii=False))

    elif args.command == "communities":
        res = detect_communities(graph)
        for c in res:
            print(f"[{c['label']}] ({c['size']} paradas)")


if __name__ == "__main__":
    main()
