import unittest
from app import create_app
from app.modules.road_network.utils.geo_utils import (
    haversine_distance,
    is_valid_coordinate,
    bounding_box_contains,
    calculate_travel_time
)
from app.modules.road_network.models import RoadNode, RoadEdge, RoadGraph
from app.modules.road_network.services import osm_service, graph_service, node_service, routing_service

TEST_BBOX = {
    'min_lat': 12.9500,
    'max_lat': 12.9800,
    'min_lng': 77.5600,
    'max_lng': 77.6000
}

class TestRoadNetworkEngine(unittest.TestCase):
    def setUp(self):
        self.app = create_app('test')
        self.client = self.app.test_client()

    def test_existing_api_v1_health(self):
        """Verify existing /api/v1/health endpoint still works without regression."""
        response = self.client.get('/api/v1/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get('status'), 'success')

    def test_road_network_health_endpoint(self):
        """Verify /api/road-network/health endpoint returns status ok and module road-network."""
        response = self.client.get('/api/road-network/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertEqual(data.get('module'), 'road-network')

    def test_road_network_status_endpoint(self):
        """Verify /api/road-network/status endpoint."""
        response = self.client.get('/api/road-network/status')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertEqual(data.get('module'), 'road-network')

    def test_road_network_config_endpoint(self):
        """Verify /api/road-network/config endpoint."""
        response = self.client.get('/api/road-network/config')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('osm_provider', data)
        self.assertIn('max_graph_nodes', data)

    def test_geo_utils_validation(self):
        """Verify coordinate validation utility."""
        self.assertTrue(is_valid_coordinate(12.9716, 77.5946))  # Bangalore
        self.assertTrue(is_valid_coordinate(-90, 180))
        self.assertFalse(is_valid_coordinate(91, 77))
        self.assertFalse(is_valid_coordinate(12, 181))
        self.assertFalse(is_valid_coordinate(None, "invalid"))

    def test_geo_utils_haversine(self):
        """Verify Haversine distance calculation (Bangalore to Mysore ~125-145 km)."""
        bangalore_lat, bangalore_lon = 12.9716, 77.5946
        mysore_lat, mysore_lon = 12.2958, 76.6394
        distance = haversine_distance(bangalore_lat, bangalore_lon, mysore_lat, mysore_lon)
        self.assertGreater(distance, 120)
        self.assertLess(distance, 150)

    def test_geo_utils_bbox_contains(self):
        """Verify bounding box containment check."""
        bbox = {'min_lat': 12.0, 'max_lat': 13.0, 'min_lng': 76.0, 'max_lng': 78.0}
        self.assertTrue(bounding_box_contains(12.5, 77.0, bbox))
        self.assertFalse(bounding_box_contains(14.0, 77.0, bbox))

    def test_geo_utils_travel_time(self):
        """Verify travel time calculation."""
        time_sec = calculate_travel_time(60.0, 60.0)
        self.assertEqual(time_sec, 3600.0)

    def test_models(self):
        """Verify RoadNode, RoadEdge, and RoadGraph model structures."""
        node1 = RoadNode(101, 12.9716, 77.5946, tags={"name": "Node 1"})
        node2 = RoadNode(102, 12.9800, 77.6000, tags={"name": "Node 2"})
        edge = RoadEdge(101, 102, distance=1.2, road_type="primary", speed_limit=60.0)

        graph = RoadGraph()
        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_edge(edge)

        self.assertEqual(len(graph.nodes), 2)
        self.assertEqual(len(graph.edges), 1)

        graph_dict = graph.to_dict()
        self.assertEqual(graph_dict["node_count"], 2)
        self.assertEqual(graph_dict["edge_count"], 1)

    def test_phase_5_2_ingestion_pipeline(self):
        """Verify complete Phase 5.2 OpenStreetMap data ingestion -> NetworkX Graph -> Validation -> Caching pipeline."""
        ingest_res = graph_service.ingest_osm_and_build(bbox=TEST_BBOX, force_refresh=True, cache_key="test_cache")
        self.assertIn(ingest_res["status"], ["built", "cached"])
        stats = ingest_res["stats"]
        self.assertGreater(stats["node_count"], 0)
        self.assertGreater(stats["edge_count"], 0)

        nx_g = graph_service.get_nx_graph()
        self.assertIsNotNone(nx_g)
        self.assertGreater(nx_g.number_of_nodes(), 0)

        nearest = node_service.find_nearest_node(12.9716, 77.5946)
        self.assertIsNotNone(nearest)
        self.assertIn("node_id", nearest)
        self.assertIn("distance_km", nearest)

    def test_ingest_api_endpoint(self):
        """Verify POST /api/road-network/ingest API endpoint."""
        response = self.client.post('/api/road-network/ingest', json={"bbox": TEST_BBOX, "force_refresh": True, "cache_key": "test_api_cache"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("stats", data.get("data", {}))

    def test_nearest_node_api_endpoint(self):
        """Verify GET /api/road-network/nodes/nearest API endpoint."""
        graph_service.ingest_osm_and_build(bbox=TEST_BBOX, cache_key="test_api_cache")
        response = self.client.get('/api/road-network/nodes/nearest?lat=12.9716&lon=77.5946')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("nearest_node", data)

    def test_routing_service_dijkstra_and_astar(self):
        """Verify Dijkstra and A* shortest path algorithms on active NetworkX graph."""
        graph_service.ingest_osm_and_build(bbox=TEST_BBOX, cache_key="test_cache")
        nx_g = graph_service.get_nx_graph()
        nodes = list(nx_g.nodes())
        self.assertGreater(len(nodes), 1)

        import networkx as nx
        src_id = nodes[0]
        reachable = list(nx.descendants(nx_g, src_id))
        if not reachable:
            # Just in case the first node is a dead-end
            src_id = nodes[1]
            reachable = list(nx.descendants(nx_g, src_id))
        tgt_id = reachable[-1]

        # Test Dijkstra
        dijkstra_route = routing_service.calculate_route(src_id, tgt_id, algorithm="dijkstra", weight="travel_time")
        self.assertEqual(dijkstra_route["algorithm"], "dijkstra")
        self.assertIn("total_distance_km", dijkstra_route)
        self.assertIn("geometry", dijkstra_route)
        self.assertGreater(len(dijkstra_route["geometry"]), 0)

        # Test A* Search
        astar_route = routing_service.calculate_route(src_id, tgt_id, algorithm="astar", weight="travel_time")
        self.assertEqual(astar_route["algorithm"], "astar")
        self.assertIn("total_distance_km", astar_route)
        self.assertEqual(astar_route["total_distance_km"], dijkstra_route["total_distance_km"])

    def test_hospet_ballari_resolution(self):
        """Verify Chitradurga/Hospet and Ballari resolve to distinct, nearby road nodes in regional graph."""
        hospet_lat, hospet_lon = 15.2700, 76.3900
        ballari_lat, ballari_lon = 15.1480, 76.9210

        hospet_res = node_service.find_nearest_node(hospet_lat, hospet_lon)
        self.assertIsNotNone(hospet_res)
        self.assertTrue(hospet_res.get("success", True))
        self.assertLess(hospet_res["distance_km"], 10.0)

        ballari_res = node_service.find_nearest_node(ballari_lat, ballari_lon)
        self.assertIsNotNone(ballari_res)
        self.assertTrue(ballari_res.get("success", True))
        self.assertLess(ballari_res["distance_km"], 10.0)

        # Ensure Hospet and Ballari do NOT resolve to the same node
        self.assertNotEqual(str(hospet_res["node_id"]), str(ballari_res["node_id"]))

    def test_bangalore_mysore_resolution(self):
        """Verify Bangalore and Mysore resolve to nearby nodes in regional graph."""
        bangalore_res = node_service.find_nearest_node(12.9716, 77.5946)
        self.assertTrue(bangalore_res.get("success", True))
        self.assertLess(bangalore_res["distance_km"], 10.0)

        mysore_res = node_service.find_nearest_node(12.2958, 76.6394)
        self.assertTrue(mysore_res.get("success", True))
        self.assertLess(mysore_res["distance_km"], 10.0)

    def test_out_of_coverage_rejection(self):
        """Verify points outside available coverage are rejected with LOCATION_OUTSIDE_ROAD_NETWORK."""
        graph_service.ingest_osm_and_build(bbox=TEST_BBOX, cache_key="test_api_cache")
        bangalore_graph = graph_service._active_graph

        # Search for London on Bangalore graph
        res = node_service.find_nearest_node(51.5074, -0.1278, graph=bangalore_graph)
        self.assertIsNotNone(res)
        self.assertFalse(res.get("success", True))
        self.assertEqual(res.get("error"), "LOCATION_OUTSIDE_ROAD_NETWORK")
        self.assertGreater(res.get("distance_km", 0), 10.0)

if __name__ == '__main__':
    unittest.main()
