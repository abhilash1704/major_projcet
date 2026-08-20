import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

import time
import logging
from app import create_app
from app.modules.road_network.services.graph_service import graph_service
from app.modules.road_network.services.routing_service import routing_service
from app.modules.vehicle_simulation.services.vehicle_generator import vehicle_generator
from app.modules.vehicle_simulation.services.vehicle_service import vehicle_service
from app.modules.traffic_intelligence.services.traffic_cost_service import traffic_cost_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("routeflow.scratch.diagnose_traffic_cost")

app = create_app("dev")

with app.app_context():
    logger.info("==================================================")
    logger.info("STARTING SPRINT 9A TRAFFIC COST BENCHMARK")
    logger.info("==================================================")

    # 1. Preload graph & compute route
    graph_service.preload_default_graph()
    nx_g = graph_service.get_nx_graph()
    if nx_g is None:
        logger.error("Failed to load graph!")
        exit(1)

    node_ids = list(nx_g.nodes())
    src_node = str(node_ids[0])
    dst_node = str(node_ids[min(500, len(node_ids) - 1)])

    route = routing_service.calculate_route(src_node, dst_node, algorithm="astar")
    path_nodes = route.get("path_nodes", [])
    geometry = route.get("geometry", [])
    route_nodes = []
    for nid, geom in zip(path_nodes, geometry):
        route_nodes.append({"id": str(nid), "lat": float(geom[0]), "lon": float(geom[1])})

    logger.info("Calculated route with %d nodes, %.2f km", len(route_nodes), route.get("total_distance_km", 0.0))

    counts_to_test = [100, 300, 500, 0]

    for count in counts_to_test:
        logger.info(f"\n==================================================")
        logger.info(f"TEST CASE: {count} vehicles")
        logger.info(f"==================================================")

        # Clear previous simulation state
        vehicle_service.delete_all_vehicles()

        if count > 0:
            gen_res = vehicle_generator.generate(count=count, seed=42, route_nodes=route_nodes)
            logger.info("Generated %d vehicles (%s mode)", gen_res.get("generated"), gen_res.get("mode"))

        # Execute Traffic Cost Engine
        t_start = time.perf_counter()
        cost_result = traffic_cost_service.calculate_traffic_costs()
        t_end = time.perf_counter()
        wall_time_ms = round((t_end - t_start) * 1000, 2)

        logger.info("Success: %s", cost_result.get("success"))
        logger.info("Active Vehicles: %d", cost_result.get("total_active_vehicles"))
        logger.info("Total Affected Edges: %d", cost_result.get("total_affected_edges"))
        logger.info("  LOW Traffic Edges: %d", cost_result.get("low_traffic_edges"))
        logger.info("  MEDIUM Traffic Edges: %d", cost_result.get("medium_traffic_edges"))
        logger.info("  HIGH Traffic Edges: %d", cost_result.get("high_traffic_edges"))
        logger.info("Engine Processing Time: %.2f ms", cost_result.get("processing_time_ms"))
        logger.info("Total Wall Clock Time: %.2f ms", wall_time_ms)

        if cost_result.get("edge_costs"):
            sample = cost_result["edge_costs"][0]
            logger.info(
                "Sample Edge [%s]: base_time=%.1fs, severity=%s, penalty=%.1fs, final_cost=%.1fs",
                sample.get("edge_id"),
                sample.get("base_travel_time_sec"),
                sample.get("traffic_level"),
                sample.get("traffic_penalty"),
                sample.get("traffic_aware_cost")
            )

    # Cleanup after test
    vehicle_service.delete_all_vehicles()
    logger.info("\nBenchmark complete.")
