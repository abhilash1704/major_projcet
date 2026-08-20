"""
Unit Tests for Road-Constrained Vehicle Trajectory Generator
"""
import unittest
from app import create_app
from app.modules.live_clustering.trajectory.generator import generator

class TestTrajectoryGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def test_trajectory_generation_in_whitefield(self):
        """Generates valid road-constrained trajectories for Whitefield."""
        with self.app.app_context():
            dataset, gt_map = generator.generate_area_trajectories(
                center_lat=12.9698,
                center_lon=77.7499,
                radius_meters=1000.0,
                area_name="Whitefield",
                num_vehicles=10,
                multi_user_ratio=0.5,
                duration_minutes=2.0,
                seed=42,
            )
            self.assertIsNotNone(dataset)
            self.assertEqual(dataset.vehicle_count, 10)
            self.assertGreater(dataset.user_count, 10)  # Multi-user carpoolers
            self.assertGreater(dataset.total_observations, 0)
            self.assertEqual(len(gt_map), dataset.user_count)

            # Verify observation schema
            obs = dataset.observations[0]
            self.assertIsNotNone(obs.observation_id)
            self.assertIsNotNone(obs.user_id)
            self.assertIsNotNone(obs.timestamp)
            self.assertGreater(obs.latitude, 0.0)
            self.assertGreater(obs.longitude, 0.0)
            self.assertGreater(obs.speed_kmh, 0.0)

    def test_multi_user_ground_truth_isolation(self):
        """Ensures ground truth map connects users to vehicles."""
        with self.app.app_context():
            dataset, gt_map = generator.generate_area_trajectories(
                center_lat=12.9174,
                center_lon=77.6228,
                radius_meters=1000.0,
                area_name="Silk Board",
                num_vehicles=5,
                seed=123,
            )
            for user_id, veh_id in gt_map.items():
                self.assertTrue(user_id.startswith("user_"))
                self.assertTrue(veh_id.startswith("veh_"))

if __name__ == "__main__":
    unittest.main()
