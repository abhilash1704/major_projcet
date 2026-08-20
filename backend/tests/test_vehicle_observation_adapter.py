"""
Unit Tests for Vehicle Observation Adapter
"""
import unittest
from app import create_app
from app.modules.live_clustering.simulation.vehicle_observation_adapter import vehicle_observation_adapter
from app.modules.live_clustering.simulation.user_observation_generator import generate_user_observations_for_vehicle

class TestVehicleObservationAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def test_user_observation_generator(self):
        vehicle = {
            "vehicle_id": "V_TEST_101",
            "latitude": 12.9174,
            "longitude": 77.6228,
            "speed_kmh": 35.0,
            "heading": 90.0,
            "current_edge": "edge_12",
        }

        obs = generate_user_observations_for_vehicle(vehicle, user_count=3, noise_radius_m=10.0)
        self.assertEqual(len(obs), 3)

        for o in obs:
            self.assertEqual(o["vehicle_source_id"], "V_TEST_101")
            self.assertTrue(o["user_id"].startswith("U_V_TEST_101_"))
            self.assertIn("latitude", o)
            self.assertIn("longitude", o)
            self.assertIn("speed_kmh", o)

    def test_adapter_get_user_observations_for_area(self):
        res = vehicle_observation_adapter.get_user_observations_for_area(
            center_lat=12.9174, center_lon=77.6228, radius_meters=1000.0
        )
        self.assertIn(res["status"], ["LIVE", "IDLE"])
        self.assertIn("user_observations", res)
        self.assertIsInstance(res["user_observations"], list)

if __name__ == "__main__":
    unittest.main()
