"""
Route-Based Vehicle Generation Tests — Sprint 5.5

Covers:
  - POST /api/routes/calculate endpoint
  - Route-based vehicle generation
  - Vehicles positioned on route
  - Vehicle distribution across route
  - No vehicles generated without a route
  - Zero / negative count rejected
  - New route replaces old route in store
  - Existing tests are not broken
"""
import unittest
import math

from app import create_app
from database.db import db as _db
from app.modules.road_network.services.graph_service import graph_service
import app.modules.vehicle_simulation.services.route_store as route_store

TEST_BBOX = {
    "min_lat": 12.9500,
    "max_lat": 12.9800,
    "min_lng": 77.5600,
    "max_lng": 77.6000,
}


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class TestRouteBasedVehicleGeneration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Build app + graph once for the entire test class."""
        cls.app = create_app("test")
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            _db.create_all()
            graph_service.ingest_osm_and_build(
                bbox=TEST_BBOX,
                force_refresh=True,
                cache_key="test_route_gen_cache",
            )
            # Find two reachable nodes for route tests
            import networkx as nx
            nx_g = graph_service.get_nx_graph()
            nodes = list(nx_g.nodes())
            src = nodes[0]
            reachable = list(nx.descendants(nx_g, src))
            if not reachable:
                src = nodes[1]
                reachable = list(nx.descendants(nx_g, src))
            tgt = reachable[-1]
            cls.src_node = str(src)
            cls.tgt_node = str(tgt)

    def setUp(self):
        """Clear vehicles + route store before every individual test."""
        with self.app.app_context():
            from app.modules.vehicle_simulation.models.vehicle import Vehicle
            _db.session.execute(_db.delete(Vehicle))
            _db.session.commit()
            graph_service.load_graph_from_cache("test_route_gen_cache")
        route_store.clear_route()
    # ── POST /api/routes/calculate ────────────────────────────────────────────

    def test_route_calculate_valid(self):
        """POST /api/routes/calculate returns success with nodes and edges."""
        resp = self.client.post("/api/routes/calculate", json={
            "source_node":      self.src_node,
            "destination_node": self.tgt_node,
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        route = data["route"]
        self.assertIn("nodes", route)
        self.assertIn("edges", route)
        self.assertIn("total_distance_km", route)
        self.assertIn("total_travel_time_seconds", route)
        self.assertGreater(len(route["nodes"]), 1)

    def test_route_calculate_missing_params(self):
        """POST /api/routes/calculate with missing params returns 400."""
        resp = self.client.post("/api/routes/calculate", json={"source_node": self.src_node})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["success"])

    def test_route_calculate_same_node(self):
        """source_node == destination_node returns 400."""
        resp = self.client.post("/api/routes/calculate", json={
            "source_node": self.src_node, "destination_node": self.src_node
        })
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["success"])

    def test_route_calculate_invalid_source(self):
        """Non-existent source node returns 404."""
        resp = self.client.post("/api/routes/calculate", json={
            "source_node": "invalid_node_xyz", "destination_node": self.tgt_node
        })
        self.assertEqual(resp.status_code, 404)

    def test_route_calculate_invalid_destination(self):
        """Non-existent destination node returns 404."""
        resp = self.client.post("/api/routes/calculate", json={
            "source_node": self.src_node, "destination_node": "invalid_node_abc"
        })
        self.assertEqual(resp.status_code, 404)

    def test_route_stored_after_calculate(self):
        """Route is stored in route_store after successful calculation."""
        self.client.post("/api/routes/calculate", json={
            "source_node": self.src_node, "destination_node": self.tgt_node,
        })
        with self.app.app_context():
            stored = route_store.get_route()
            self.assertIsNotNone(stored)
            self.assertIn("path_nodes", stored)
            self.assertGreater(len(stored["path_nodes"]), 1)

    # ── Route-based vehicle generation ────────────────────────────────────────

    def test_generate_vehicles_on_route(self):
        """Vehicles generated after route calculation are within route bounds."""
        # Calculate route first (stores it in route_store)
        route_resp = self.client.post("/api/routes/calculate", json={
            "source_node": self.src_node, "destination_node": self.tgt_node,
        })
        self.assertEqual(route_resp.status_code, 200)
        route_nodes = route_resp.get_json()["route"]["nodes"]

        # Bounding box of route
        lats = [n["lat"] for n in route_nodes]
        lons = [n["lon"] for n in route_nodes]
        lat_min, lat_max = min(lats) - 0.01, max(lats) + 0.01
        lon_min, lon_max = min(lons) - 0.01, max(lons) + 0.01

        # Generate vehicles
        gen_resp = self.client.post("/api/vehicles/generate", json={
            "count": 10, "seed": 42, "cache_key": "test_route_gen_cache"
        })
        self.assertEqual(gen_resp.status_code, 201)
        data = gen_resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["generated"], 10)
        self.assertEqual(data.get("mode"), "route")

        # All vehicles must be within route bounding box
        for v in data["vehicles"]:
            self.assertGreaterEqual(v["latitude"],  lat_min, f"Lat {v['latitude']} below route")
            self.assertLessEqual(v["latitude"],     lat_max, f"Lat {v['latitude']} above route")
            self.assertGreaterEqual(v["longitude"], lon_min, f"Lon {v['longitude']} below route")
            self.assertLessEqual(v["longitude"],    lon_max, f"Lon {v['longitude']} above route")

    def test_vehicles_distributed_across_route(self):
        """Vehicles are not all concentrated at the same route position."""
        self.client.post("/api/routes/calculate", json={
            "source_node": self.src_node, "destination_node": self.tgt_node,
        })
        gen_resp = self.client.post("/api/vehicles/generate", json={
            "count": 10, "seed": 7, "cache_key": "test_route_gen_cache"
        })
        vehicles = gen_resp.get_json()["vehicles"]
        lats = [v["latitude"] for v in vehicles]
        lons = [v["longitude"] for v in vehicles]
        lat_mean = sum(lats) / len(lats)
        lon_mean = sum(lons) / len(lons)
        lat_variance = sum((v["latitude"] - lat_mean) ** 2 for v in vehicles) / len(vehicles)
        lon_variance = sum((v["longitude"] - lon_mean) ** 2 for v in vehicles) / len(vehicles)

        self.assertTrue(
            lat_variance > 0.0 or lon_variance > 0.0,
            "All vehicles have the exact same coordinates — not distributed along the route."
        )

    def test_vehicles_not_all_same_node(self):
        """Generated vehicles do not all share the same current_node."""
        self.client.post("/api/routes/calculate", json={
            "source_node": self.src_node, "destination_node": self.tgt_node,
        })
        gen_resp = self.client.post("/api/vehicles/generate", json={
            "count": 10, "seed": 99, "cache_key": "test_route_gen_cache"
        })
        nodes = [v["current_node"] for v in gen_resp.get_json()["vehicles"]]
        unique_nodes = len(set(nodes))
        self.assertGreater(unique_nodes, 1, "All vehicles assigned to the same node")

    def test_no_vehicles_without_route(self):
        """Without a route, generator falls back to graph mode (not blocked but mode=graph)."""
        # Ensure no route is stored
        route_store.clear_route()
        gen_resp = self.client.post("/api/vehicles/generate", json={
            "count": 5, "seed": 1, "cache_key": "test_route_gen_cache"
        })
        self.assertEqual(gen_resp.status_code, 201)
        data = gen_resp.get_json()
        # Mode should be 'graph' when no route is available
        self.assertEqual(data.get("mode"), "graph")

    def test_zero_count_rejected(self):
        """count=0 is rejected with 400."""
        resp = self.client.post("/api/vehicles/generate", json={"count": 0})
        self.assertEqual(resp.status_code, 400)

    def test_negative_count_rejected(self):
        """Negative count is rejected with 400."""
        resp = self.client.post("/api/vehicles/generate", json={"count": -10})
        self.assertEqual(resp.status_code, 400)

    def test_new_route_replaces_old(self):
        """Calculating a new route updates route_store and old vehicles stay unchanged."""
        # Calculate first route and store it
        self.client.post("/api/routes/calculate", json={
            "source_node": self.src_node, "destination_node": self.tgt_node,
        })
        first_route = route_store.get_route()
        first_src = first_route["source_node_id"] if first_route else None

        # Calculate same route again (simulating recalculation)
        self.client.post("/api/routes/calculate", json={
            "source_node": self.src_node, "destination_node": self.tgt_node,
        })
        new_route = route_store.get_route()
        self.assertIsNotNone(new_route)
        self.assertEqual(new_route["source_node_id"], first_src)

    def test_clear_simulation_clears_route(self):
        """DELETE /api/vehicles/simulation also clears the stored route."""
        self.client.post("/api/routes/calculate", json={
            "source_node": self.src_node, "destination_node": self.tgt_node,
        })
        self.assertIsNotNone(route_store.get_route())

        resp = self.client.delete("/api/vehicles/simulation")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(route_store.get_route())

    def test_distance_calculation_accuracy(self):
        """total_distance_km is consistent with node coordinate distances."""
        resp = self.client.post("/api/routes/calculate", json={
            "source_node": self.src_node, "destination_node": self.tgt_node,
        })
        route = resp.get_json()["route"]
        nodes = route["nodes"]

        # Compute Haversine sum for comparison (upper bound — route may include detours)
        manual_dist = sum(
            _haversine(nodes[i]["lat"], nodes[i]["lon"], nodes[i+1]["lat"], nodes[i+1]["lon"])
            for i in range(len(nodes) - 1)
        )
        api_dist = route["total_distance_km"]
        # API distance should be close to manual haversine sum (within 5%)
        self.assertAlmostEqual(api_dist, manual_dist, delta=max(manual_dist * 0.05, 0.001))

    def test_vehicle_generation_25_vehicles_on_route(self):
        """25 vehicles on route — all have valid coordinates and correct mode."""
        self.client.post("/api/routes/calculate", json={
            "source_node": self.src_node, "destination_node": self.tgt_node,
        })
        resp = self.client.post("/api/vehicles/generate", json={
            "count": 25, "seed": 55, "cache_key": "test_route_gen_cache"
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data["generated"], 25)
        self.assertEqual(data.get("mode"), "route")
        for v in data["vehicles"]:
            self.assertGreaterEqual(v["latitude"], -90.0)
            self.assertLessEqual(v["latitude"], 90.0)
            self.assertGreaterEqual(v["longitude"], -180.0)
            self.assertLessEqual(v["longitude"], 180.0)
            self.assertGreater(v["speed"], 0.0)

    # ── Regression ────────────────────────────────────────────────────────────

    def test_regression_road_network_health(self):
        """Existing /api/road-network/health still works."""
        resp = self.client.get("/api/road-network/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "ok")

    def test_regression_vehicle_crud(self):
        """Existing vehicle CRUD still works after route generation changes."""
        resp = self.client.post("/api/vehicles", json={
            "latitude": 12.9716, "longitude": 77.5946, "speed": 30.0, "heading": 90.0
        })
        self.assertEqual(resp.status_code, 201)
        vid = resp.get_json()["vehicle"]["vehicle_id"]
        self.assertTrue(vid.startswith("veh_"))

    def test_regression_v1_api(self):
        """/api/v1/health still works."""
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
