"""
Sprint 9B Diagnostic Benchmark Script
Tests A* and Dijkstra under NORMAL and TRAFFIC_AWARE modes across 0, 100, 300, and 500 vehicle scenarios.
"""
import time
import math
from flask import Flask
from app.services.routing_service import routing_service
from app.modules.road_network.services.graph_service import graph_service
from app.modules.traffic_intelligence.services.traffic_cost_service import traffic_cost_service


def run_diagnostics():
    app = Flask(__name__)
    app.config["TRAFFIC_PENALTY_FACTOR_LOW"] = 1.15
    app.config["TRAFFIC_PENALTY_FACTOR_MEDIUM"] = 1.60
    app.config["TRAFFIC_PENALTY_FACTOR_HIGH"] = 3.00

    with app.app_context():
        print("=========================================================================")
        print("          ROUTEFLOW SPRINT 9B — ROUTING & TRAFFIC BENCHMARK              ")
        print("=========================================================================")

        # Load road graph or initialize benchmark grid
        nx_g = graph_service.get_nx_graph()
        if nx_g is None or len(nx_g) == 0:
            try:
                graph_service._load_from_cache()
                nx_g = graph_service.get_nx_graph()
            except Exception:
                pass

        if nx_g is None or len(nx_g) == 0:
            print("No cached graph found — generating 20x20 synthetic road network graph for benchmark...")
            import networkx as nx
            G = nx.grid_2d_graph(20, 20, create_using=nx.MultiDiGraph)
            nx_g = nx.MultiDiGraph()
            for u, v in G.edges():
                u_str = f"{u[0]}_{u[1]}"
                v_str = f"{v[0]}_{v[1]}"
                u_lat, u_lon = 12.97 + u[0] * 0.001, 77.59 + u[1] * 0.001
                v_lat, v_lon = 12.97 + v[0] * 0.001, 77.59 + v[1] * 0.001
                nx_g.add_node(u_str, lat=u_lat, lon=u_lon)
                nx_g.add_node(v_str, lat=v_lat, lon=v_lon)
                # Length 100m (0.1km), travel time 10s
                nx_g.add_edge(u_str, v_str, key=0, length=100.0, travel_time=10.0)
            graph_service._nx_graph = nx_g

        print(f"Road Graph Status: Loaded ({nx_g.number_of_nodes()} nodes, {nx_g.number_of_edges()} edges)")

        nodes = list(nx_g.nodes())
        if len(nodes) < 2:
            print("Error: Graph has fewer than 2 nodes. Cannot benchmark.")
            return

        # Pick source & destination nodes (first and node ~100 steps away)
        src_node = nodes[0]
        dst_node = nodes[min(100, len(nodes) - 1)]

        print(f"Test Route Nodes: Source='{src_node}', Destination='{dst_node}'\n")

        vehicle_counts = [0, 100, 300, 500]
        algorithms = ["astar", "dijkstra"]
        modes = ["normal", "traffic_aware"]

        results = []

        for v_count in vehicle_counts:
            print(f"--- Benchmark Scenario: {v_count} Vehicles ---")

            # Mock vehicles on graph edges for benchmarking
            mock_vehicles = []
            edges = list(nx_g.edges(keys=True))
            for i in range(v_count):
                u, v, k = edges[i % len(edges)]
                e_key = f"{u}-{v}-{k}"
                mock_vehicles.append({
                    "id": f"veh_{i}",
                    "current_edge": e_key,
                    "latitude": nx_g.nodes[u].get("lat", 0.0),
                    "longitude": nx_g.nodes[u].get("lon", 0.0),
                    "speed": 25.0
                })

            # Mock snapshot & calculation
            traffic_cost_service.invalidate_cache()
            mock_snapshot = {"vehicles": mock_vehicles}
            
            # Monkeypatch snapshot for benchmark
            from app.modules.traffic_intelligence.services.traffic_data_service import traffic_data_service
            traffic_data_service.get_active_vehicle_snapshot = lambda: mock_snapshot

            # Precompute traffic costs
            cost_info = traffic_cost_service.get_cached_costs()
            affected = cost_info.get("total_affected_edges", 0)
            print(f"  Traffic Cost Calc: Affected Edges = {affected} | Calc Time = {cost_info.get('processing_time_ms')}ms")

            for algo in algorithms:
                for mode in modes:
                    # Invalidate route service internal LRU cache for fair measurement
                    from app.services.routing_service import _route_cache
                    _route_cache.clear()

                    t0 = time.perf_counter()
                    res = routing_service.calculate_route(
                        source_node=src_node,
                        destination_node=dst_node,
                        algorithm=algo,
                        routing_mode=mode
                    )
                    t1 = time.perf_counter()
                    elapsed_ms = round((t1 - t0) * 1000, 2)

                    row = {
                        "vehicles": v_count,
                        "algorithm": algo.upper(),
                        "mode": mode.upper(),
                        "success": res.get("success", False),
                        "distance_km": res.get("distance_km", 0.0),
                        "node_count": len(res.get("nodes", [])),
                        "base_cost": res.get("base_cost", 0.0),
                        "traffic_cost": res.get("traffic_cost", 0.0),
                        "total_cost": res.get("total_cost", 0.0),
                        "traffic_level": res.get("traffic_level", "NONE"),
                        "time_ms": elapsed_ms
                    }
                    results.append(row)
                    print(
                        f"  [{algo.upper():8s} | {mode.upper():13s}] "
                        f"Found: {row['success']} | Nodes: {row['node_count']:4d} | "
                        f"Dist: {row['distance_km']:6.2f}km | BaseCost: {row['base_cost']:6.1f}s | "
                        f"TrafficCost: {row['traffic_cost']:6.1f}s | TotalCost: {row['total_cost']:6.1f}s | "
                        f"Time: {row['time_ms']:6.2f}ms"
                    )
            print()

        print("=========================================================================")
        print("                           BENCHMARK SUMMARY                             ")
        print("=========================================================================")
        print(f"{'Vehicles':<10}{'Algorithm':<12}{'Mode':<15}{'Nodes':<8}{'Dist(km)':<10}{'TotalCost(s)':<15}{'Time(ms)':<10}")
        print("-" * 80)
        for r in results:
            print(f"{r['vehicles']:<10}{r['algorithm']:<12}{r['mode']:<15}{r['node_count']:<8}{r['distance_km']:<10.2f}{r['total_cost']:<15.1f}{r['time_ms']:<10.2f}")
        print("=========================================================================\n")


if __name__ == "__main__":
    run_diagnostics()
