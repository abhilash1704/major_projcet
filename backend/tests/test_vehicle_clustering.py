"""
Unit Tests for DBSCAN Vehicle Clustering Engine
"""
import unittest
from app import create_app
from app.modules.live_clustering.clustering.vehicle_cluster_service import vehicle_cluster_service

class TestVehicleClustering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def test_vehicle_clustering_groups_co_located_users(self):
        """Co-located users in the same carpool are clustered together."""
        observations = [
            # Vehicle 1 users (Silk Board)
            {"observation_id": "o1", "user_id": "u1", "latitude": 12.9174, "longitude": 77.6228, "speed_kmh": 30.0, "heading": 90.0},
            {"observation_id": "o2", "user_id": "u2", "latitude": 12.91741, "longitude": 77.62281, "speed_kmh": 30.2, "heading": 90.5},
            {"observation_id": "o3", "user_id": "u3", "latitude": 12.91739, "longitude": 77.62279, "speed_kmh": 29.8, "heading": 89.5},
            
            # Vehicle 2 users (50m away)
            {"observation_id": "o4", "user_id": "u4", "latitude": 12.9185, "longitude": 77.6238, "speed_kmh": 45.0, "heading": 180.0},
            {"observation_id": "o5", "user_id": "u5", "latitude": 12.91851, "longitude": 77.62381, "speed_kmh": 45.1, "heading": 180.2},
        ]

        res = vehicle_cluster_service.compute_vehicle_clusters(observations, 12.9174, 77.6228)
        self.assertEqual(res["status"], "ACTIVE")
        clusters = res["clusters"]
        self.assertEqual(len(clusters), 2)

        # Check vehicle metrics
        metrics = res["metrics"]
        self.assertEqual(metrics["total_active_users"], 5)
        self.assertEqual(metrics["estimated_vehicles"], 2)
        self.assertEqual(metrics["users_grouped"], 3)  # 5 users - 2 vehicles = 3 grouped users

    def test_ground_truth_id_not_used_in_clustering(self):
        """Ensures clustering function operates without ground truth vehicle IDs."""
        obs = [
            {"observation_id": "o1", "user_id": "u1", "latitude": 12.9174, "longitude": 77.6228, "speed_kmh": 30.0, "heading": 90.0},
            {"observation_id": "o2", "user_id": "u2", "latitude": 12.91741, "longitude": 77.62281, "speed_kmh": 30.2, "heading": 90.5},
        ]
        res = vehicle_cluster_service.compute_vehicle_clusters(obs, 12.9174, 77.6228)
        self.assertEqual(res["status"], "ACTIVE")
        self.assertNotIn("ground_truth_vehicle_id", res["clusters"][0])

if __name__ == "__main__":
    unittest.main()
