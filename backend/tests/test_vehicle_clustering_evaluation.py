"""
Unit Tests for Ground Truth Vehicle Clustering Evaluation Engine
"""
import unittest
from app import create_app
from app.modules.live_clustering.evaluation.clustering_metrics import evaluation_engine

class TestVehicleClusteringEvaluation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def test_evaluation_metrics_perfect_clustering(self):
        """Tests count error, precision, recall, F1, and purity on perfect clustering."""
        clusters = [
            {"cluster_id": "c1", "user_ids": ["u1", "u2", "u3"]},
            {"cluster_id": "c2", "user_ids": ["u4", "u5"]},
        ]

        ground_truth_map = {
            "u1": "v1", "u2": "v1", "u3": "v1",
            "u4": "v2", "u5": "v2",
        }

        res = evaluation_engine.evaluate_clustering(clusters, ground_truth_map, actual_vehicle_count=2)
        self.assertEqual(res["status"], "ACTIVE")
        self.assertEqual(res["actual_vehicle_count"], 2)
        self.assertEqual(res["estimated_vehicle_count"], 2)
        self.assertEqual(res["absolute_error"], 0)
        self.assertEqual(res["percentage_error"], 0.0)
        self.assertEqual(res["precision"], 1.0)
        self.assertEqual(res["recall"], 1.0)
        self.assertEqual(res["f1_score"], 1.0)
        self.assertEqual(res["cluster_purity"], 1.0)

    def test_evaluation_metrics_with_count_error(self):
        """Tests evaluation when estimated vehicle count differs from ground truth."""
        # 3 clusters generated when actual ground truth was 2 vehicles
        clusters = [
            {"cluster_id": "c1", "user_ids": ["u1", "u2"]},
            {"cluster_id": "c2", "user_ids": ["u3"]},
            {"cluster_id": "c3", "user_ids": ["u4", "u5"]},
        ]

        ground_truth_map = {
            "u1": "v1", "u2": "v1", "u3": "v1",
            "u4": "v2", "u5": "v2",
        }

        res = evaluation_engine.evaluate_clustering(clusters, ground_truth_map, actual_vehicle_count=2)
        self.assertEqual(res["actual_vehicle_count"], 2)
        self.assertEqual(res["estimated_vehicle_count"], 3)
        self.assertEqual(res["absolute_error"], 1)
        self.assertEqual(res["percentage_error"], 50.0)
        self.assertGreater(res["precision"], 0.0)
        self.assertGreater(res["recall"], 0.0)

if __name__ == "__main__":
    unittest.main()
