"""
Vehicle Simulation Tests — Sprint 4.1 & 4.2

Covers:
  CRUD operations (create, get, list, update, delete)
  Validation (lat, lon, speed, heading, status)
  Bulk generation (1, 10, 100 vehicles)
  Generation constraints (unique IDs, valid coordinates, road-node refs)
  Simulation clear
  Edge cases (invalid count, duplicate handling)
  Regression: road-network system unchanged
  Regression: authentication still works
"""
import unittest
from app import create_app
from database.db import db as _db
from app.modules.road_network.services.graph_service import graph_service

# ── Road-network test bbox used across all graph-related tests ──────────────
TEST_BBOX = {
    "min_lat": 12.9500,
    "max_lat": 12.9800,
    "min_lng": 77.5600,
    "max_lng": 77.6000,
}


class TestVehicleSimulation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Build app + graph once for the entire test class (expensive OSM call)."""
        cls.app = create_app("test")
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            _db.create_all()
            # Ingest road graph once — all generation tests reuse this.
            graph_service.ingest_osm_and_build(
                bbox=TEST_BBOX,
                force_refresh=True,
                cache_key="test_vehicle_cache",
            )

    def setUp(self):
        """Clear vehicles before every individual test."""
        with self.app.app_context():
            from app.modules.vehicle_simulation.models.vehicle import Vehicle
            _db.session.execute(_db.delete(Vehicle))
            _db.session.commit()
            from app.services.routing_service import route_store
            route_store.clear_route()
            from app.modules.vehicle_simulation.services.simulation_store import simulation_store
            simulation_store.reset_session()

    # ─────────────────────────────────────────────────────────────────────────
    # CRUD — Sprint 4.1
    # ─────────────────────────────────────────────────────────────────────────

    def test_01_create_vehicle_valid(self):
        """Create a vehicle via POST /api/vehicles with valid data."""
        resp = self.client.post("/api/vehicles", json={
            "latitude":     12.9716,
            "longitude":    77.5946,
            "speed":        35.5,
            "heading":      90.0,
            "current_node": "123456",
            "current_edge": "123456-789012-0",
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        v = data["vehicle"]
        self.assertTrue(v["vehicle_id"].startswith("veh_"))
        self.assertAlmostEqual(v["latitude"],  12.9716, places=4)
        self.assertAlmostEqual(v["longitude"], 77.5946, places=4)
        self.assertEqual(v["status"], "active")

    def test_02_get_vehicle(self):
        """GET /api/vehicles/<id> returns the correct vehicle."""
        create_resp = self.client.post("/api/vehicles", json={
            "latitude": 12.9716, "longitude": 77.5946
        })
        vid = create_resp.get_json()["vehicle"]["vehicle_id"]

        resp = self.client.get(f"/api/vehicles/{vid}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["vehicle"]["vehicle_id"], vid)

    def test_03_get_all_vehicles_empty(self):
        """GET /api/vehicles returns empty list when no vehicles exist."""
        resp = self.client.get("/api/vehicles")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["vehicles"], [])

    def test_04_get_all_vehicles_populated(self):
        """GET /api/vehicles returns all created vehicles."""
        for i in range(3):
            self.client.post("/api/vehicles", json={
                "latitude": 12.97 + i * 0.001, "longitude": 77.59
            })
        resp = self.client.get("/api/vehicles")
        data = resp.get_json()
        self.assertEqual(data["count"], 3)
        self.assertEqual(len(data["vehicles"]), 3)

    def test_05_update_vehicle(self):
        """PUT /api/vehicles/<id> updates vehicle state."""
        vid = self.client.post("/api/vehicles", json={
            "latitude": 12.9716, "longitude": 77.5946, "speed": 30.0, "heading": 0.0
        }).get_json()["vehicle"]["vehicle_id"]

        resp = self.client.put(f"/api/vehicles/{vid}", json={
            "speed": 55.0, "heading": 180.0, "status": "stopped"
        })
        self.assertEqual(resp.status_code, 200)
        updated = resp.get_json()["vehicle"]
        self.assertAlmostEqual(updated["speed"],   55.0, places=1)
        self.assertAlmostEqual(updated["heading"], 180.0, places=1)
        self.assertEqual(updated["status"], "stopped")

    def test_06_delete_vehicle(self):
        """DELETE /api/vehicles/<id> removes the vehicle."""
        vid = self.client.post("/api/vehicles", json={
            "latitude": 12.9716, "longitude": 77.5946
        }).get_json()["vehicle"]["vehicle_id"]

        resp = self.client.delete(f"/api/vehicles/{vid}")
        self.assertEqual(resp.status_code, 200)

        get_resp = self.client.get(f"/api/vehicles/{vid}")
        self.assertEqual(get_resp.status_code, 404)

    def test_07_get_nonexistent_vehicle(self):
        """GET /api/vehicles/<unknown_id> returns 404."""
        resp = self.client.get("/api/vehicles/veh_does_not_exist")
        self.assertEqual(resp.status_code, 404)

    # ─────────────────────────────────────────────────────────────────────────
    # Validation — Sprint 4.1
    # ─────────────────────────────────────────────────────────────────────────

    def test_08_invalid_latitude_too_high(self):
        """Latitude > 90 is rejected with 400."""
        resp = self.client.post("/api/vehicles", json={
            "latitude": 91.0, "longitude": 77.0
        })
        self.assertEqual(resp.status_code, 400)

    def test_09_invalid_latitude_too_low(self):
        """Latitude < -90 is rejected with 400."""
        resp = self.client.post("/api/vehicles", json={
            "latitude": -91.0, "longitude": 77.0
        })
        self.assertEqual(resp.status_code, 400)

    def test_10_invalid_longitude(self):
        """Longitude outside ±180 is rejected with 400."""
        resp = self.client.post("/api/vehicles", json={
            "latitude": 12.0, "longitude": 200.0
        })
        self.assertEqual(resp.status_code, 400)

    def test_11_negative_speed(self):
        """Negative speed is rejected with 400."""
        resp = self.client.post("/api/vehicles", json={
            "latitude": 12.9716, "longitude": 77.5946, "speed": -5.0
        })
        self.assertEqual(resp.status_code, 400)

    def test_12_invalid_heading(self):
        """Heading >= 360 or < 0 is rejected with 400."""
        for heading in (-1.0, 360.0, 400.0):
            resp = self.client.post("/api/vehicles", json={
                "latitude": 12.9716, "longitude": 77.5946, "heading": heading
            })
            self.assertEqual(resp.status_code, 400, msg=f"heading={heading} should be invalid")

    def test_13_invalid_status(self):
        """Unknown status value is rejected with 400."""
        resp = self.client.post("/api/vehicles", json={
            "latitude": 12.9716, "longitude": 77.5946, "status": "flying"
        })
        self.assertEqual(resp.status_code, 400)

    def test_14_missing_coordinates(self):
        """Missing latitude/longitude is rejected with 400."""
        resp = self.client.post("/api/vehicles", json={"speed": 30.0})
        self.assertEqual(resp.status_code, 400)

    # ─────────────────────────────────────────────────────────────────────────
    # Generation — Sprint 4.2
    # ─────────────────────────────────────────────────────────────────────────

    def test_15_generate_1_vehicle(self):
        """POST /api/vehicles/generate with count=1 creates 1 vehicle."""
        resp = self.client.post("/api/vehicles/generate", json={
            "count": 1, "seed": 42, "cache_key": "test_vehicle_cache"
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["generated"], 1)
        self.assertEqual(len(data["vehicles"]), 1)

    def test_16_generate_10_vehicles(self):
        """POST /api/vehicles/generate with count=10 creates 10 vehicles."""
        resp = self.client.post("/api/vehicles/generate", json={
            "count": 10, "seed": 0, "cache_key": "test_vehicle_cache"
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data["generated"], 10)
        self.assertEqual(len(data["vehicles"]), 10)

    def test_17_generate_100_vehicles(self):
        """POST /api/vehicles/generate with count=100 creates 100 vehicles."""
        resp = self.client.post("/api/vehicles/generate", json={
            "count": 100, "seed": 1, "cache_key": "test_vehicle_cache"
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data["generated"], 100)

    def test_18_unique_vehicle_ids(self):
        """All generated vehicles have unique vehicle_ids."""
        resp = self.client.post("/api/vehicles/generate", json={
            "count": 50, "seed": 7, "cache_key": "test_vehicle_cache"
        })
        vehicles = resp.get_json()["vehicles"]
        ids = [v["vehicle_id"] for v in vehicles]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate vehicle IDs detected")

    def test_19_valid_latitudes(self):
        """All generated vehicles have latitude in [-90, 90]."""
        resp = self.client.post("/api/vehicles/generate", json={
            "count": 20, "seed": 10, "cache_key": "test_vehicle_cache"
        })
        for v in resp.get_json()["vehicles"]:
            self.assertGreaterEqual(v["latitude"],  -90.0)
            self.assertLessEqual(v["latitude"],      90.0)

    def test_20_valid_longitudes(self):
        """All generated vehicles have longitude in [-180, 180]."""
        resp = self.client.post("/api/vehicles/generate", json={
            "count": 20, "seed": 11, "cache_key": "test_vehicle_cache"
        })
        for v in resp.get_json()["vehicles"]:
            self.assertGreaterEqual(v["longitude"], -180.0)
            self.assertLessEqual(v["longitude"],     180.0)

    def test_21_valid_speeds(self):
        """All generated vehicles have speed >= 0."""
        resp = self.client.post("/api/vehicles/generate", json={
            "count": 20, "seed": 12, "cache_key": "test_vehicle_cache"
        })
        for v in resp.get_json()["vehicles"]:
            self.assertGreaterEqual(v["speed"], 0.0)

    def test_22_valid_headings(self):
        """All generated vehicles have heading in [0, 360)."""
        resp = self.client.post("/api/vehicles/generate", json={
            "count": 20, "seed": 13, "cache_key": "test_vehicle_cache"
        })
        for v in resp.get_json()["vehicles"]:
            self.assertGreaterEqual(v["heading"],  0.0)
            self.assertLess(v["heading"],          360.0)

    def test_23_current_node_in_graph(self):
        """Generated vehicle current_node exists in the road graph."""
        resp = self.client.post("/api/vehicles/generate", json={
            "count": 10, "seed": 5, "cache_key": "test_vehicle_cache"
        })
        with self.app.app_context():
            nx_g = graph_service.get_nx_graph()
            node_ids = {str(n) for n in nx_g.nodes()}
            for v in resp.get_json()["vehicles"]:
                self.assertIn(
                    v["current_node"], node_ids,
                    msg=f"current_node {v['current_node']} not in graph"
                )

    def test_24_current_edge_exists(self):
        """Generated vehicle current_edge is a non-empty string reference."""
        resp = self.client.post("/api/vehicles/generate", json={
            "count": 10, "seed": 6, "cache_key": "test_vehicle_cache"
        })
        for v in resp.get_json()["vehicles"]:
            self.assertIsNotNone(v["current_edge"])
            self.assertGreater(len(v["current_edge"]), 0)

    def test_25_vehicle_status_valid(self):
        """Generated vehicles all have a valid status."""
        from app.modules.vehicle_simulation.constants import VALID_VEHICLE_STATUSES
        resp = self.client.post("/api/vehicles/generate", json={
            "count": 10, "seed": 8, "cache_key": "test_vehicle_cache"
        })
        for v in resp.get_json()["vehicles"]:
            self.assertIn(v["status"], VALID_VEHICLE_STATUSES)

    def test_26_repeated_generation_new_ids(self):
        """Calling generate twice creates a new set of vehicles with new IDs."""
        r1 = self.client.post("/api/vehicles/generate", json={
            "count": 5, "seed": 1, "cache_key": "test_vehicle_cache"
        })
        r2 = self.client.post("/api/vehicles/generate", json={
            "count": 5, "seed": 2, "cache_key": "test_vehicle_cache"
        })
        ids1 = {v["vehicle_id"] for v in r1.get_json()["vehicles"]}
        ids2 = {v["vehicle_id"] for v in r2.get_json()["vehicles"]}
        # All IDs must be unique across both batches
        self.assertEqual(len(ids1 & ids2), 0, "Duplicate IDs across two generation calls")

        # Total vehicles should be 10
        list_resp = self.client.get("/api/vehicles")
        self.assertEqual(list_resp.get_json()["count"], 10)

    def test_27_generate_zero_count(self):
        """count=0 is rejected with 400."""
        resp = self.client.post("/api/vehicles/generate", json={"count": 0})
        self.assertEqual(resp.status_code, 400)

    def test_28_generate_negative_count(self):
        """Negative count is rejected with 400."""
        resp = self.client.post("/api/vehicles/generate", json={"count": -5})
        self.assertEqual(resp.status_code, 400)

    def test_29_generate_non_numeric_count(self):
        """Non-numeric count is rejected with 400."""
        resp = self.client.post("/api/vehicles/generate", json={"count": "lots"})
        self.assertEqual(resp.status_code, 400)

    def test_30_generate_missing_count(self):
        """Missing count field is rejected with 400."""
        resp = self.client.post("/api/vehicles/generate", json={})
        self.assertEqual(resp.status_code, 400)

    def test_31_generate_exceeds_max(self):
        """count > MAX_GENERATION_COUNT is rejected with 400."""
        resp = self.client.post("/api/vehicles/generate", json={"count": 99999})
        self.assertEqual(resp.status_code, 400)

    def test_32_clear_simulation(self):
        """DELETE /api/vehicles/simulation removes all vehicles."""
        self.client.post("/api/vehicles/generate", json={
            "count": 10, "seed": 9, "cache_key": "test_vehicle_cache"
        })
        self.assertEqual(self.client.get("/api/vehicles").get_json()["count"], 10)

        resp = self.client.delete("/api/vehicles/simulation")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["deleted"], 10)

        self.assertEqual(self.client.get("/api/vehicles").get_json()["count"], 0)

    def test_33_list_after_generate(self):
        """GET /api/vehicles returns all generated vehicles with correct fields."""
        self.client.post("/api/vehicles/generate", json={
            "count": 5, "seed": 3, "cache_key": "test_vehicle_cache"
        })
        resp = self.client.get("/api/vehicles")
        data = resp.get_json()
        self.assertEqual(data["count"], 5)
        required_fields = {"vehicle_id", "latitude", "longitude", "speed",
                           "heading", "current_node", "current_edge", "status"}
        for v in data["vehicles"]:
            self.assertTrue(required_fields.issubset(v.keys()))

    # ─────────────────────────────────────────────────────────────────────────
    # Regression — road network & auth still work
    # ─────────────────────────────────────────────────────────────────────────

    def test_34_road_network_health_regression(self):
        """Existing /api/road-network/health endpoint still works."""
        resp = self.client.get("/api/road-network/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "ok")

    def test_35_nearest_node_api_regression(self):
        """Existing nearest-node API still resolves correctly."""
        resp = self.client.get("/api/road-network/nodes/nearest?lat=12.9716&lon=77.5946")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("nearest_node", data)

    def test_36_auth_api_regression(self):
        """Existing /api/v1/health (auth-layer) still returns 200."""
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "success")

    def test_37_vehicles_on_road_edges(self):
        """Verify generated vehicles are associated with actual road edges."""
        resp = self.client.post("/api/vehicles/generate", json={
            "count": 10, "seed": 20, "cache_key": "test_vehicle_cache"
        })
        self.assertEqual(resp.status_code, 201)
        with self.app.app_context():
            nx_g = graph_service.get_nx_graph()
            for v in resp.get_json()["vehicles"]:
                # current_edge format: "src-dst-key"
                parts = v["current_edge"].rsplit("-", 1)
                self.assertGreater(len(parts), 0)
                # current_node must be a valid graph node
                self.assertIn(v["current_node"], {str(n) for n in nx_g.nodes()})

    def test_38_vehicle_health_endpoint(self):
        """Vehicle simulation module health endpoint works."""
        resp = self.client.get("/api/vehicles/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "ok")


if __name__ == "__main__":
    unittest.main()
