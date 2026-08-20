import unittest
from unittest.mock import patch
from app import create_app
from database.db import db as _db
from app.modules.traffic_intelligence.services.dbscan_service import dbscan_service

def create_mock_vehicle(vid, lat, lon, speed):
    return {
        "vehicle_id": vid,
        "latitude": lat,
        "longitude": lon,
        "speed_kmh": speed,
        "status": "ACTIVE"
    }

class TestTrafficClusters(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app("test")
        with cls.app.app_context():
            _db.create_all()

    @patch('app.modules.traffic_intelligence.services.dbscan_service.traffic_data_service')
    def test_empty_vehicles(self, mock_data_service):
        mock_data_service.get_active_vehicle_snapshot.return_value = {
            "timestamp": "2023-01-01T00:00:00Z",
            "vehicle_count": 0,
            "vehicles": []
        }
        
        with self.app.app_context():
            result = dbscan_service.get_clusters()
            
        self.assertTrue(result["success"])
        self.assertEqual(result["vehicle_count"], 0)
        self.assertEqual(result["cluster_count"], 0)
        self.assertEqual(result["noise_vehicle_count"], 0)
        self.assertEqual(len(result["clusters"]), 0)

    @patch('app.modules.traffic_intelligence.services.dbscan_service.traffic_data_service')
    def test_too_few_vehicles(self, mock_data_service):
        mock_data_service.get_active_vehicle_snapshot.return_value = {
            "timestamp": "2023-01-01T00:00:00Z",
            "vehicle_count": 3,
            "vehicles": [
                create_mock_vehicle("v1", 12.0, 77.0, 20),
                create_mock_vehicle("v2", 12.0, 77.0, 20),
                create_mock_vehicle("v3", 12.0, 77.0, 20)
            ]
        }
        
        with self.app.app_context():
            result = dbscan_service.get_clusters()
            
        self.assertTrue(result["success"])
        self.assertEqual(result["cluster_count"], 0)
        self.assertEqual(result["noise_vehicle_count"], 3)

    @patch('app.modules.traffic_intelligence.services.dbscan_service.traffic_data_service')
    def test_distinct_clusters(self, mock_data_service):
        # Group A - close together
        group_a = [create_mock_vehicle(f"a{i}", 12.9716 + (i * 0.0001), 77.5946 + (i * 0.0001), 10) for i in range(5)]
        # Group B - close together, but far from A
        group_b = [create_mock_vehicle(f"b{i}", 13.9716 + (i * 0.0001), 78.5946 + (i * 0.0001), 30) for i in range(6)]
        # Noise
        noise = [create_mock_vehicle("n1", 0.0, 0.0, 0)]
        
        mock_data_service.get_active_vehicle_snapshot.return_value = {
            "timestamp": "2023-01-01T00:00:00Z",
            "vehicle_count": 12,
            "vehicles": group_a + group_b + noise
        }
        
        with self.app.app_context():
            self.app.config['DBSCAN_EPS_METERS'] = 500
            self.app.config['DBSCAN_MIN_SAMPLES'] = 5
            result = dbscan_service.get_clusters()
            
        self.assertTrue(result["success"])
        self.assertEqual(result["cluster_count"], 2)
        self.assertEqual(result["noise_vehicle_count"], 1)
        
        clusters = result["clusters"]
        self.assertTrue(any(c["vehicle_count"] == 5 for c in clusters))
        self.assertTrue(any(c["vehicle_count"] == 6 for c in clusters))
        self.assertTrue(all(c["radius_meters"] >= 0 for c in clusters))
