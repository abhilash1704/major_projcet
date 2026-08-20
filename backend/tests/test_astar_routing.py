import unittest
from app import create_app
from app.modules.road_network.services import node_service, graph_service, routing_service

# Sample coordinates for real locations
LOCATIONS = {
    "davanagere": (14.4644, 75.9218),
    "ballari": (15.1480, 76.9210),
    "hosapete": (15.2700, 76.3900),
    "chitradurga": (14.2250, 76.4000),
    "kalasa": (13.2320, 75.3620),
    "shivamogga": (13.9299, 75.5681),
}

class TestAStarRouteCalculation(unittest.TestCase):
    def setUp(self):
        self.app = create_app('test')
        self.client = self.app.test_client()

    def test_negative_source_equals_destination(self):
        """Verify source == destination produces controlled 400 validation error."""
        response = self.client.post('/api/routes/calculate', json={
            "source_node": "1000",
            "destination_node": "1000"
        })
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertIn("must be different", data["error"])

    def test_negative_invalid_source_node(self):
        """Verify invalid source node produces controlled 404 error."""
        response = self.client.post('/api/routes/calculate', json={
            "source_node": "999999999999999",
            "destination_node": "1000"
        })
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Source node", data["error"])
        self.assertIn("is not present in the routing graph", data["error"])

    def test_negative_invalid_destination_node(self):
        """Verify invalid destination node produces controlled 404 error."""
        nx_g = graph_service.get_nx_graph()
        valid_src = list(nx_g.nodes())[0] if nx_g and len(nx_g) > 0 else "1000"
        response = self.client.post('/api/routes/calculate', json={
            "source_node": str(valid_src),
            "destination_node": "999999999999999"
        })
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Destination node", data["error"])
        self.assertIn("is not present in the routing graph", data["error"])

    def test_davanagere_to_ballari_routing(self):
        """Test A* routing: Davanagere -> Ballari."""
        src_lat, src_lon = LOCATIONS["davanagere"]
        dst_lat, dst_lon = LOCATIONS["ballari"]

        graph_service.ensure_graph_for_points(src_lat, src_lon, dst_lat, dst_lon)
        src_node = node_service.find_nearest_node(src_lat, src_lon)
        dst_node = node_service.find_nearest_node(dst_lat, dst_lon)

        self.assertTrue(src_node.get("success"))
        self.assertTrue(dst_node.get("success"))

        response = self.client.post('/api/routes/calculate', json={
            "source_node": src_node["node_id"],
            "destination_node": dst_node["node_id"],
            "source_lat": src_lat,
            "source_lon": src_lon,
            "destination_lat": dst_lat,
            "destination_lon": dst_lon,
            "algorithm": "astar"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        route = data["route"]
        self.assertEqual(route["algorithm"], "astar")
        self.assertGreater(route["total_distance_km"], 0.0)
        self.assertGreater(route["total_travel_time_seconds"], 0.0)
        self.assertGreater(len(route["nodes"]), 1)
        self.assertGreater(len(route["edges"]), 0)

    def test_ballari_to_hosapete_routing(self):
        """Test A* routing: Ballari -> Hosapete."""
        src_lat, src_lon = LOCATIONS["ballari"]
        dst_lat, dst_lon = LOCATIONS["hosapete"]

        graph_service.ensure_graph_for_points(src_lat, src_lon, dst_lat, dst_lon)
        src_node = node_service.find_nearest_node(src_lat, src_lon)
        dst_node = node_service.find_nearest_node(dst_lat, dst_lon)

        response = self.client.post('/api/routes/calculate', json={
            "source_node": src_node["node_id"],
            "destination_node": dst_node["node_id"],
            "source_lat": src_lat,
            "source_lon": src_lon,
            "destination_lat": dst_lat,
            "destination_lon": dst_lon,
            "algorithm": "astar"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        route = data["route"]
        self.assertGreater(route["total_distance_km"], 0.0)

    def test_ballari_to_chitradurga_routing(self):
        """Test A* routing: Ballari -> Chitradurga."""
        src_lat, src_lon = LOCATIONS["ballari"]
        dst_lat, dst_lon = LOCATIONS["chitradurga"]

        graph_service.ensure_graph_for_points(src_lat, src_lon, dst_lat, dst_lon)
        src_node = node_service.find_nearest_node(src_lat, src_lon)
        dst_node = node_service.find_nearest_node(dst_lat, dst_lon)

        response = self.client.post('/api/routes/calculate', json={
            "source_node": src_node["node_id"],
            "destination_node": dst_node["node_id"],
            "source_lat": src_lat,
            "source_lon": src_lon,
            "destination_lat": dst_lat,
            "destination_lon": dst_lon,
            "algorithm": "astar"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        route = data["route"]
        self.assertGreater(route["total_distance_km"], 0.0)

    def test_kalasa_to_shivamogga_routing(self):
        """Test A* routing: Kalasa -> Shivamogga."""
        src_lat, src_lon = LOCATIONS["kalasa"]
        dst_lat, dst_lon = LOCATIONS["shivamogga"]

        graph_service.ensure_graph_for_points(src_lat, src_lon, dst_lat, dst_lon)
        src_node = node_service.find_nearest_node(src_lat, src_lon)
        dst_node = node_service.find_nearest_node(dst_lat, dst_lon)

        response = self.client.post('/api/routes/calculate', json={
            "source_node": src_node["node_id"],
            "destination_node": dst_node["node_id"],
            "source_lat": src_lat,
            "source_lon": src_lon,
            "destination_lat": dst_lat,
            "destination_lon": dst_lon,
            "algorithm": "astar"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        route = data["route"]
        self.assertGreater(route["total_distance_km"], 0.0)

if __name__ == '__main__':
    unittest.main()
