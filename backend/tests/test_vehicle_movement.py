"""
Vehicle Movement Service Tests — Sprint 4.3

Tests:
  1.  Update moves active vehicles
  2.  Vehicles' coordinates change after an update
  3.  edge_progress advances after an update
  4.  Vehicles on short edges transition to the next edge
  5.  Multi-edge traversal with large delta_seconds works
  6.  Stopped vehicles are not moved
  7.  update with delta_seconds=0 returns 400
  8.  update with negative delta_seconds returns 400
  9.  update with delta_seconds > MAX is rejected
  10. update with no vehicles returns success (no crash)
  11. Snapshot endpoint returns all vehicles
  12. edge_progress in [0, 1] after update
  13. heading stays valid [0, 360) after update
  14. Coordinates remain geographically valid after update
  15. current_node is a valid graph node after edge transition
  16. Regression: existing road-network tests unchanged
  17. Regression: existing auth tests unchanged
"""
import unittest
from app import create_app
from database.db import db as _db
from app.modules.road_network.services.graph_service import graph_service

TEST_BBOX = {
    "min_lat": 12.9500,
    "max_lat": 12.9800,
    "min_lng": 77.5600,
    "max_lng": 77.6000,
}


class TestVehicleMovementService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Build app + ingest road graph once for the whole class."""
        cls.app = create_app("test")
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            _db.create_all()
            graph_service.ingest_osm_and_build(
                bbox=TEST_BBOX,
                force_refresh=True,
                cache_key="test_movement_cache",
            )

    def setUp(self):
        """Clear all vehicles before each test."""
        with self.app.app_context():
            from app.modules.vehicle_simulation.models.vehicle import Vehicle
            _db.session.execute(_db.delete(Vehicle))
            _db.session.commit()
            from app.services.routing_service import route_store
            route_store.clear_route()
            from app.modules.vehicle_simulation.services.simulation_store import simulation_store
            simulation_store.reset_session()

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _generate(self, count=5, seed=42):
        return self.client.post("/api/vehicles/generate", json={
            "count": count, "seed": seed, "cache_key": "test_movement_cache"
        })

    def _update(self, delta_seconds=1.0, seed=0):
        return self.client.post("/api/vehicles/simulation/update", json={
            "delta_seconds": delta_seconds, "seed": seed, "cache_key": "test_movement_cache"
        })

    # ── Tests ──────────────────────────────────────────────────────────────────

    def test_01_update_succeeds(self):
        """POST /api/vehicles/simulation/update with delta_seconds=1 returns success."""
        self._generate(5, seed=1)
        resp = self._update(1.0)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["delta_seconds"], 1.0)

    def test_02_update_moves_vehicles(self):
        """After an update, at least some vehicles have moved (coordinates changed)."""
        gen_resp = self._generate(10, seed=2)
        before = {v["vehicle_id"]: (v["latitude"], v["longitude"])
                  for v in gen_resp.get_json()["vehicles"]}

        self._update(5.0, seed=2)

        after_resp = self.client.get("/api/vehicles")
        after = {v["vehicle_id"]: (v["latitude"], v["longitude"])
                 for v in after_resp.get_json()["vehicles"]}

        moved = sum(1 for vid in before if before[vid] != after.get(vid, before[vid]))
        self.assertGreater(moved, 0, "Expected at least one vehicle to move after 5 seconds")

    def test_03_edge_progress_advances(self):
        """edge_progress increases after an update for active vehicles (if on same edge)."""
        gen_resp = self._generate(5, seed=3)
        initial_state = {v["vehicle_id"]: {"prog": v["edge_progress"], "edge": v["current_edge"]}
                         for v in gen_resp.get_json()["vehicles"]}

        self._update(1.0, seed=3)

        after_resp = self.client.get("/api/vehicles")
        for v in after_resp.get_json()["vehicles"]:
            if v["status"] == "active":
                init = initial_state.get(v["vehicle_id"])
                if init and v["current_edge"] == init["edge"]:
                    self.assertGreaterEqual(
                        v["edge_progress"],
                        init["prog"],
                        msg=f"edge_progress should not decrease on the same edge for vehicle {v['vehicle_id']}"
                    )

    def test_04_multi_edge_traversal(self):
        """Large delta_seconds causes edge transitions without crashing."""
        self._generate(5, seed=4)
        # 3600 seconds = 1 hour. At ~35km/h, it will cross many short city edges.
        resp = self._update(3600.0, seed=4)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["delta_seconds"], 3600.0)
        self.assertGreater(data["vehicles_moved"] + data["vehicles_stopped"], 0)

    def test_05_stopped_vehicle_not_moved(self):
        """A manually stopped vehicle is not advanced by update."""
        gen_resp = self._generate(2, seed=5)
        vid = gen_resp.get_json()["vehicles"][0]["vehicle_id"]

        # Stop it manually
        self.client.put(f"/api/vehicles/{vid}", json={"status": "stopped"})
        v_before = self.client.get(f"/api/vehicles/{vid}").get_json()["vehicle"]
        lat_before = v_before["latitude"]
        lon_before = v_before["longitude"]

        self._update(5.0, seed=5)

        v_after = self.client.get(f"/api/vehicles/{vid}").get_json()["vehicle"]
        self.assertEqual(v_after["latitude"],  lat_before)
        self.assertEqual(v_after["longitude"], lon_before)

    def test_06_update_zero_delta(self):
        """delta_seconds=0 is rejected with 400."""
        resp = self.client.post("/api/vehicles/simulation/update", json={"delta_seconds": 0})
        self.assertEqual(resp.status_code, 400)

    def test_07_update_negative_delta(self):
        """Negative delta_seconds is rejected with 400."""
        resp = self.client.post("/api/vehicles/simulation/update", json={"delta_seconds": -5.0})
        self.assertEqual(resp.status_code, 400)

    def test_08_update_exceeds_max(self):
        """delta_seconds > 3600 is rejected with 400."""
        resp = self.client.post("/api/vehicles/simulation/update", json={"delta_seconds": 99999})
        self.assertEqual(resp.status_code, 400)

    def test_09_update_with_no_vehicles(self):
        """Update with empty vehicle table returns success without crashing."""
        resp = self._update(1.0)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["vehicles_moved"], 0)

    def test_10_snapshot_endpoint(self):
        """GET /api/vehicles/snapshot returns all vehicles."""
        self._generate(5, seed=6)
        resp = self.client.get("/api/vehicles/snapshot")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["count"], 5)
        self.assertEqual(len(data["vehicles"]), 5)

    def test_11_edge_progress_valid_range(self):
        """edge_progress stays in [0, 1] after multiple updates."""
        self._generate(10, seed=7)
        self._update(20.0, seed=7)

        resp = self.client.get("/api/vehicles")
        for v in resp.get_json()["vehicles"]:
            self.assertGreaterEqual(v["edge_progress"], 0.0)
            self.assertLessEqual(v["edge_progress"],    1.0)

    def test_12_heading_valid_after_update(self):
        """heading stays in [0, 360) after updates."""
        self._generate(10, seed=8)
        self._update(30.0, seed=8)

        resp = self.client.get("/api/vehicles")
        for v in resp.get_json()["vehicles"]:
            self.assertGreaterEqual(v["heading"],  0.0)
            self.assertLess(v["heading"],          360.0)

    def test_13_coordinates_valid_after_update(self):
        """Lat/lon remain in valid geographic bounds after updates."""
        self._generate(10, seed=9)
        self._update(15.0, seed=9)

        resp = self.client.get("/api/vehicles")
        for v in resp.get_json()["vehicles"]:
            self.assertGreaterEqual(v["latitude"],  -90.0)
            self.assertLessEqual(v["latitude"],      90.0)
            self.assertGreaterEqual(v["longitude"], -180.0)
            self.assertLessEqual(v["longitude"],     180.0)

    def test_14_current_node_valid_after_transition(self):
        """current_node after transitions is still a valid graph node."""
        self._generate(10, seed=10)
        self._update(300.0, seed=10)  # long enough to force edge transitions

        with self.app.app_context():
            nx_g = graph_service.get_nx_graph()
            valid_node_ids = {str(n) for n in nx_g.nodes()}

        resp = self.client.get("/api/vehicles")
        for v in resp.get_json()["vehicles"]:
            if v["current_node"] is not None:
                self.assertIn(
                    v["current_node"], valid_node_ids,
                    msg=f"current_node {v['current_node']} is not a valid graph node"
                )

    def test_15_snapshot_has_required_fields(self):
        """Snapshot vehicles contain all required fields."""
        self._generate(3, seed=11)
        self._update(5.0, seed=11)

        resp = self.client.get("/api/vehicles/snapshot")
        required = {"vehicle_id", "latitude", "longitude", "speed",
                    "heading", "current_node", "current_edge", "edge_progress", "status"}
        for v in resp.get_json()["vehicles"]:
            self.assertTrue(required.issubset(v.keys()))

    def test_16_update_non_numeric_rejected(self):
        """Non-numeric delta_seconds value is rejected with 400."""
        resp = self.client.post("/api/vehicles/simulation/update", json={"delta_seconds": "many"})
        self.assertEqual(resp.status_code, 400)

    # ── Regression ─────────────────────────────────────────────────────────────

    def test_17_road_network_health_regression(self):
        """/api/road-network/health still works after movement engine is registered."""
        resp = self.client.get("/api/road-network/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "ok")

    def test_18_nearest_node_regression(self):
        """Nearest-node API is unaffected by movement engine."""
        resp = self.client.get("/api/road-network/nodes/nearest?lat=12.9716&lon=77.5946")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "success")

    def test_19_auth_regression(self):
        """/api/v1/health (auth layer) still works."""
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "success")


if __name__ == "__main__":
    unittest.main()
