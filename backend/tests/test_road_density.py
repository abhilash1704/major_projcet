"""
Unit Tests for Road Density Mapper
"""
import unittest
from app import create_app
from app.modules.live_clustering.road_mapping.cluster_road_mapper import cluster_road_mapper

class TestRoadDensityMapper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def test_compute_road_density_from_clusters(self):
        clusters = [
            {
                "cluster_id": "c1",
                "center_latitude": 12.9174,
                "center_longitude": 77.6228,
                "primary_road_edge_id": "edge_100",
            },
            {
                "cluster_id": "c2",
                "center_latitude": 12.9175,
                "center_longitude": 77.6229,
                "primary_road_edge_id": "edge_100",
            },
        ]

        res = cluster_road_mapper.compute_road_density(clusters, 12.9174, 77.6228)
        self.assertEqual(res["status"], "ACTIVE")
        self.assertGreaterEqual(res["total_active_edges"], 1)

        segments = res["road_segments"]
        self.assertTrue(len(segments) > 0)
        self.assertIn("density_rank", segments[0])
        self.assertIn("vehicle_count", segments[0])

if __name__ == "__main__":
    unittest.main()
