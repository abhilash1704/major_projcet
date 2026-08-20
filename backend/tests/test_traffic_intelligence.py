import unittest
import time
from app import create_app
from database.db import db as _db
from app.modules.vehicle_simulation.models.vehicle import Vehicle
from app.modules.vehicle_simulation.constants import VEHICLE_STATUS_ACTIVE, VEHICLE_STATUS_STOPPED
from app.modules.traffic_intelligence.services.traffic_density_service import traffic_density_service
from app.modules.traffic_intelligence.services.traffic_data_service import traffic_data_service


class TestTrafficIntelligence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app("test")
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            _db.create_all()

    def setUp(self):
        with self.app.app_context():
            _db.session.execute(_db.delete(Vehicle))
            _db.session.commit()
            from app.services.routing_service import route_store
            route_store.clear_route()
            from app.modules.vehicle_simulation.services.simulation_store import simulation_store
            simulation_store.reset_session()

    def _create_vehicle(self, lat, lon, speed=0.0, status=VEHICLE_STATUS_ACTIVE):
        v = Vehicle(latitude=lat, longitude=lon, speed=speed, status=status)
        _db.session.add(v)
        _db.session.commit()

        from app.modules.vehicle_simulation.services.simulation_store import simulation_store
        v_dict = {
            "vehicle_id": v.vehicle_id,
            "latitude": lat,
            "longitude": lon,
            "speed": speed,
            "status": status,
            "current_node": getattr(v, "current_node", None),
            "current_edge": getattr(v, "current_edge", None)
        }
        simulation_store._vehicles[v.vehicle_id] = v_dict
        return v

    # ── Sprint 6.1: Live Simulated Vehicle Position Data Layer Tests ───────────

    def test_no_active_vehicles(self):
        """TEST 1: 0 vehicles -> count 0, vehicles []"""
        resp = self.client.get("/api/traffic-intelligence/vehicles")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["vehicle_count"], 0)
        self.assertEqual(data["vehicles"], [])
        self.assertIn("timestamp", data)

    def test_one_active_vehicle(self):
        """TEST 2: 1 vehicle -> correctly appears"""
        with self.app.app_context():
            self._create_vehicle(12.9716, 77.5946, 35.5)
            
        resp = self.client.get("/api/traffic-intelligence/vehicles")
        data = resp.get_json()
        self.assertEqual(data["vehicle_count"], 1)
        self.assertEqual(len(data["vehicles"]), 1)
        v = data["vehicles"][0]
        self.assertEqual(v["latitude"], 12.9716)
        self.assertEqual(v["longitude"], 77.5946)
        self.assertEqual(v["speed_kmh"], 35.5)
        self.assertEqual(v["status"], VEHICLE_STATUS_ACTIVE)

    def test_multiple_active_vehicles(self):
        """TEST 3: Multiple active vehicles -> all returned"""
        with self.app.app_context():
            self._create_vehicle(12.9716, 77.5946, 35.5)
            self._create_vehicle(12.9800, 77.6000, 40.0)
            
        resp = self.client.get("/api/traffic-intelligence/vehicles")
        data = resp.get_json()
        self.assertEqual(data["vehicle_count"], 2)

    def test_inactive_vehicle_excluded(self):
        """TEST 4: Inactive vehicle -> excluded"""
        with self.app.app_context():
            self._create_vehicle(12.9716, 77.5946, 35.5, status=VEHICLE_STATUS_STOPPED)
            
        resp = self.client.get("/api/traffic-intelligence/vehicles")
        data = resp.get_json()
        self.assertEqual(data["vehicle_count"], 0)

    def test_invalid_coordinates_excluded(self):
        """TEST 5, 6, 7, 8, 9: Invalid coordinates -> excluded"""
        with self.app.app_context():
            from app.modules.vehicle_simulation.services.simulation_store import simulation_store
            simulation_store._vehicles['veh_invalid1'] = {"vehicle_id": "veh_invalid1", "latitude": 95.0, "longitude": 77.5946, "speed": 0.0, "status": "active"}
            simulation_store._vehicles['veh_invalid2'] = {"vehicle_id": "veh_invalid2", "latitude": 12.9716, "longitude": 200.0, "speed": 0.0, "status": "active"}
            
        resp = self.client.get("/api/traffic-intelligence/vehicles")
        data = resp.get_json()
        self.assertEqual(data["vehicle_count"], 0)

    # ── Sprint 6.2: Traffic Density Engine Tests ──────────────────────────────

    def test_density_zero_vehicles(self):
        """TEST 1: 0 vehicles -> 0 cells"""
        resp = self.client.get("/api/traffic-intelligence/density")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["vehicle_count"], 0)
        self.assertEqual(data["cell_count"], 0)
        self.assertEqual(data["cells"], [])

    def test_density_one_vehicle(self):
        """TEST 2: 1 vehicle -> 1 occupied cell"""
        with self.app.app_context():
            self._create_vehicle(12.9716, 77.5946, 30.0)
            
        resp = self.client.get("/api/traffic-intelligence/density?cell_size_meters=500")
        data = resp.get_json()
        self.assertEqual(data["vehicle_count"], 1)
        self.assertEqual(data["cell_count"], 1)
        
        cell = data["cells"][0]
        self.assertEqual(cell["vehicle_count"], 1)
        self.assertEqual(cell["average_speed_kmh"], 30.0)
        self.assertEqual(cell["area_km2"], 0.25)
        self.assertEqual(cell["density_vehicles_per_km2"], 4.0)
        self.assertEqual(cell["density_level"], "LOW")

    def test_density_multiple_vehicles_same_area(self):
        """TEST 3: Multiple vehicles in same area -> 1 cell with increased count"""
        with self.app.app_context():
            # These are extremely close, definitely within same 500m cell
            self._create_vehicle(12.97160, 77.59460, 30.0)
            self._create_vehicle(12.97161, 77.59461, 50.0)
            
        resp = self.client.get("/api/traffic-intelligence/density?cell_size_meters=500")
        data = resp.get_json()
        self.assertEqual(data["cell_count"], 1)
        
        cell = data["cells"][0]
        self.assertEqual(cell["vehicle_count"], 2)
        self.assertEqual(cell["average_speed_kmh"], 40.0)

    def test_density_multiple_areas(self):
        """TEST 4: Vehicles in separate areas -> multiple cells"""
        with self.app.app_context():
            self._create_vehicle(12.9716, 77.5946)
            self._create_vehicle(13.9716, 78.5946) # completely different cell
            
        resp = self.client.get("/api/traffic-intelligence/density?cell_size_meters=500")
        data = resp.get_json()
        self.assertEqual(data["cell_count"], 2)

    def test_density_classification_thresholds(self):
        """TEST 9: Classification -> LOW, MEDIUM, HIGH"""
        with self.app.app_context():
            # Put 35 vehicles in the exact same cell to trigger HIGH
            for _ in range(35):
                self._create_vehicle(12.9716, 77.5946, 10.0)
            
        resp = self.client.get("/api/traffic-intelligence/density?cell_size_meters=500")
        data = resp.get_json()
        self.assertEqual(data["cell_count"], 1)
        self.assertEqual(data["cells"][0]["density_level"], "HIGH")

    def test_performance_300_vehicles(self):
        """TEST 10: Performance test for 300 vehicles < 100ms"""
        with self.app.app_context():
            for i in range(300):
                self._create_vehicle(12.9716 + (i * 0.0001), 77.5946, 20.0)
            
        start = time.perf_counter()
        resp = self.client.get("/api/traffic-intelligence/density")
        duration = time.perf_counter() - start
        
        self.assertEqual(resp.status_code, 200)
        self.assertLess(duration, 0.1, "Density calculation for 300 vehicles took longer than 100ms")
