import unittest
import networkx as nx
from flask import Flask
from app.modules.road_network.services.graph_service import graph_service
from app.services.routing_service import routing_service
from api.routes_blueprint import routes_bp

TEST_BBOX = {
    'min_lat': 12.9500,
    'max_lat': 12.9800,
    'min_lng': 77.5600,
    'max_lng': 77.6000
}


class TestDijkstraAndAStarRouting(unittest.TestCase):
    """
    Sprint 5.3 Unit Tests for Dijkstra Routing and A* Algorithm Comparison.
    """

    @classmethod
    def setUpClass(cls):
        """Set up Flask test application and synthetic road graph cache."""
        cls.app = Flask(__name__)
        cls.app.config["TESTING"] = True
        cls.app.register_blueprint(routes_bp)
        cls.client = cls.app.test_client()

        # Ingest/build graph for consistent isolated testing
        graph_service.ingest_osm_and_build(
            bbox=TEST_BBOX,
            cache_key="test_dijkstra_cache"
        )
        cls.graph = graph_service.get_nx_graph()
        cls.nodes = list(cls.graph.nodes)

    def test_01_default_algorithm_is_astar(self):
        """Verify that omitting the algorithm defaults to 'astar'."""
        src = str(self.nodes[0])
        reachable = list(nx.descendants(self.graph, src))
        tgt = str(reachable[-1] if reachable else self.nodes[-1])

        res = routing_service.calculate_route(src, tgt)
        self.assertEqual(res["algorithm"], "astar")
        self.assertTrue(res["success"])
        self.assertGreater(len(res["nodes"]), 0)

    def test_02_dijkstra_algorithm_selection(self):
        """Verify explicit Dijkstra routing algorithm selection."""
        src = str(self.nodes[0])
        reachable = list(nx.descendants(self.graph, src))
        tgt = str(reachable[-1] if reachable else self.nodes[-1])

        res = routing_service.calculate_route(src, tgt, algorithm="dijkstra")
        self.assertEqual(res["algorithm"], "dijkstra")
        self.assertTrue(res["success"])
        self.assertGreater(len(res["nodes"]), 0)

    def test_03_invalid_algorithm_returns_400(self):
        """Verify that supplying an unsupported algorithm returns HTTP 400."""
        src = str(self.nodes[0])
        tgt = str(self.nodes[1])

        response = self.client.post("/api/routes/calculate", json={
            "source_node": src,
            "destination_node": tgt,
            "algorithm": "bfs_unsupported"
        })
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Unsupported routing algorithm", data["error"])

    def test_04_shared_edge_cost_and_optimal_metrics(self):
        """
        Verify both A* and Dijkstra compute equal optimal total distance & travel time
        given the exact same graph and edge costs.
        """
        src = str(self.nodes[0])
        reachable = list(nx.descendants(self.graph, src))
        tgt = str(reachable[-1] if reachable else self.nodes[-1])

        astar_res = routing_service.calculate_route(src, tgt, algorithm="astar")
        dijkstra_res = routing_service.calculate_route(src, tgt, algorithm="dijkstra")

        # Total distance and total travel time should match
        self.assertAlmostEqual(astar_res["total_distance_km"], dijkstra_res["total_distance_km"], places=2)
        self.assertAlmostEqual(astar_res["total_travel_time_seconds"], dijkstra_res["total_travel_time_seconds"], places=1)
        self.assertEqual(astar_res["eta_minutes"], dijkstra_res["eta_minutes"])

    def test_05_same_source_and_destination(self):
        """Verify source == destination raises ValueError / HTTP 400."""
        src = str(self.nodes[0])
        response = self.client.post("/api/routes/calculate", json={
            "source_node": src,
            "destination_node": src,
            "algorithm": "dijkstra"
        })
        self.assertEqual(response.status_code, 400)

    def test_06_invalid_source_or_destination(self):
        """Verify missing source/destination node returns HTTP 404."""
        src = str(self.nodes[0])
        bogus = "non_existent_node_9999999"

        # Invalid source
        resp_src = self.client.post("/api/routes/calculate", json={
            "source_node": bogus,
            "destination_node": src,
            "algorithm": "dijkstra"
        })
        self.assertEqual(resp_src.status_code, 404)

        # Invalid destination
        resp_tgt = self.client.post("/api/routes/calculate", json={
            "source_node": src,
            "destination_node": bogus,
            "algorithm": "dijkstra"
        })
        self.assertEqual(resp_tgt.status_code, 404)

    def test_07_algorithm_comparison_method(self):
        """Verify routing_service.compare_algorithms method output."""
        src = str(self.nodes[0])
        reachable = list(nx.descendants(self.graph, src))
        tgt = str(reachable[-1] if reachable else self.nodes[-1])

        res = routing_service.compare_algorithms(src, tgt)
        self.assertTrue(res["success"])
        self.assertIn("comparison", res)
        comp = res["comparison"]
        self.assertIn("astar", comp)
        self.assertIn("dijkstra", comp)

        self.assertIn("execution_time_ms", comp["astar"])
        self.assertIn("route_nodes", comp["astar"])
        self.assertIn("distance_km", comp["astar"])
        self.assertIn("travel_time_seconds", comp["astar"])

        self.assertEqual(comp["astar"]["distance_km"], comp["dijkstra"]["distance_km"])

    def test_08_algorithm_comparison_endpoint(self):
        """Verify POST /api/routes/compare API endpoint."""
        src = str(self.nodes[0])
        reachable = list(nx.descendants(self.graph, src))
        tgt = str(reachable[-1] if reachable else self.nodes[-1])

        response = self.client.post("/api/routes/compare", json={
            "source_node": src,
            "destination_node": tgt
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIn("comparison", data)


if __name__ == "__main__":
    unittest.main()
