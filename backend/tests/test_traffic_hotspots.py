import unittest
from unittest.mock import patch
from app import create_app
from database.db import db as _db
from app.modules.traffic_intelligence.services.hotspot_service import hotspot_service

def create_mock_cluster(cid, count, density, speed):
    return {
        "cluster_id": cid,
        "center_latitude": 12.9716,
        "center_longitude": 77.5946,
        "vehicle_count": count,
        "density_vehicles_per_km2": density,
        "average_speed_kmh": speed,
        "radius_meters": 100
    }

class TestTrafficHotspots(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app("test")
        with cls.app.app_context():
            _db.create_all()

    @patch('app.modules.traffic_intelligence.services.hotspot_service.dbscan_service')
    def test_empty_clusters(self, mock_dbscan_service):
        mock_dbscan_service.get_clusters.return_value = {
            "timestamp": "2023-01-01T00:00:00Z",
            "vehicle_count": 0,
            "cluster_count": 0,
            "clusters": []
        }
        
        with self.app.app_context():
            result = hotspot_service.detect_hotspots()
            
        self.assertTrue(result["success"])
        self.assertEqual(result["hotspot_count"], 0)
        self.assertEqual(len(result["hotspots"]), 0)

    @patch('app.modules.traffic_intelligence.services.hotspot_service.dbscan_service')
    def test_no_eligible_hotspots(self, mock_dbscan_service):
        # Creates a cluster below HOTSPOT_MIN_VEHICLES (5)
        mock_dbscan_service.get_clusters.return_value = {
            "timestamp": "2023-01-01T00:00:00Z",
            "vehicle_count": 4,
            "cluster_count": 1,
            "clusters": [
                create_mock_cluster(1, 4, 100.0, 20.0) # count=4 fails min 5
            ]
        }
        
        with self.app.app_context():
            result = hotspot_service.detect_hotspots()
            
        self.assertTrue(result["success"])
        self.assertEqual(result["cluster_count"], 1)
        self.assertEqual(result["hotspot_count"], 0)

    @patch('app.modules.traffic_intelligence.services.hotspot_service.dbscan_service')
    def test_hotspot_severity(self, mock_dbscan_service):
        # A: HIGH (lots of vehicles, high density, low speed)
        # B: MEDIUM (moderate everything)
        # C: LOW (just meets thresholds, ok speed)
        mock_dbscan_service.get_clusters.return_value = {
            "timestamp": "2023-01-01T00:00:00Z",
            "vehicle_count": 130,
            "cluster_count": 3,
            "clusters": [
                create_mock_cluster(1, 100, 300.0, 5.0), # HIGH
                create_mock_cluster(2, 20, 100.0, 30.0), # MEDIUM
                create_mock_cluster(3, 10, 20.0, 50.0)   # LOW
            ]
        }
        
        with self.app.app_context():
            result = hotspot_service.detect_hotspots()
            
        self.assertTrue(result["success"])
        self.assertEqual(result["hotspot_count"], 3)
        
        hotspots = result["hotspots"]
        
        # Verify sorting by score DESC
        self.assertTrue(hotspots[0]["hotspot_score"] >= hotspots[1]["hotspot_score"])
        self.assertTrue(hotspots[1]["hotspot_score"] >= hotspots[2]["hotspot_score"])
        
        # Check severities
        severities = [h["severity"] for h in hotspots]
        self.assertIn("HIGH", severities)
        self.assertIn("MEDIUM", severities)
        self.assertIn("LOW", severities)
