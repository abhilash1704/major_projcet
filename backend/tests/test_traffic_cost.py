"""
Unit Tests for Traffic Cost Service — Sprint 9A
"""
import unittest
from unittest.mock import patch, MagicMock
from app import create_app
from database.db import db as _db
from app.modules.traffic_intelligence.services.traffic_cost_service import traffic_cost_service


class TestTrafficCostService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app("test")
        with cls.app.app_context():
            _db.create_all()

    @patch('app.modules.traffic_intelligence.services.traffic_cost_service.traffic_data_service')
    def test_zero_vehicles(self, mock_data_service):
        mock_data_service.get_active_vehicle_snapshot.return_value = {
            "timestamp": "2026-08-12T00:00:00Z",
            "vehicle_count": 0,
            "vehicles": []
        }

        with self.app.app_context():
            result = traffic_cost_service.calculate_traffic_costs()

        self.assertTrue(result["success"])
        self.assertEqual(result["total_active_vehicles"], 0)
        self.assertEqual(result["total_affected_edges"], 0)
        self.assertEqual(result["low_traffic_edges"], 0)
        self.assertEqual(result["medium_traffic_edges"], 0)
        self.assertEqual(result["high_traffic_edges"], 0)
        self.assertIn("processing_time_ms", result)

    @patch('app.modules.traffic_intelligence.services.traffic_cost_service.traffic_data_service')
    @patch('app.modules.traffic_intelligence.services.traffic_cost_service.hotspot_service')
    def test_cost_calculation_levels(self, mock_hotspot_service, mock_data_service):
        # Mock 16 vehicles on edge_1 (HIGH >= 15)
        # Mock 6 vehicles on edge_2 (MEDIUM >= 5)
        # Mock 2 vehicles on edge_3 (LOW >= 1)
        vehicles = []
        for i in range(16):
            vehicles.append({"vehicle_id": f"v1_{i}", "latitude": 12.97, "longitude": 77.59, "current_edge": "100-200-0"})
        for i in range(6):
            vehicles.append({"vehicle_id": f"v2_{i}", "latitude": 12.98, "longitude": 77.60, "current_edge": "200-300-0"})
        for i in range(2):
            vehicles.append({"vehicle_id": f"v3_{i}", "latitude": 12.99, "longitude": 77.61, "current_edge": "300-400-0"})

        mock_data_service.get_active_vehicle_snapshot.return_value = {
            "timestamp": "2026-08-12T00:00:00Z",
            "vehicle_count": len(vehicles),
            "vehicles": vehicles
        }

        mock_hotspot_service.detect_hotspots.return_value = {
            "success": True,
            "hotspots": []
        }

        # Mock NetworkX graph
        mock_nx_g = MagicMock()
        mock_nx_g.nodes.return_value = {}
        mock_nx_g.__len__.return_value = 100
        mock_nx_g.get_edge_data.side_effect = lambda u, v: {0: {"length": 1.0, "travel_time": 60.0}}

        with patch('app.modules.road_network.services.graph_service.graph_service.get_nx_graph', return_value=mock_nx_g):
            with self.app.app_context():
                result = traffic_cost_service.calculate_traffic_costs()

        self.assertTrue(result["success"])
        self.assertEqual(result["total_active_vehicles"], 24)
        self.assertEqual(result["total_affected_edges"], 3)
        self.assertEqual(result["high_traffic_edges"], 1)
        self.assertEqual(result["medium_traffic_edges"], 1)
        self.assertEqual(result["low_traffic_edges"], 1)

    def test_cost_endpoint_route(self):
        client = self.app.test_client()
        response = client.get('/api/traffic-intelligence/costs')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertTrue(json_data["success"])
        self.assertIn("total_active_vehicles", json_data)
        self.assertIn("total_affected_edges", json_data)
        self.assertIn("processing_time_ms", json_data)


if __name__ == '__main__':
    unittest.main()
