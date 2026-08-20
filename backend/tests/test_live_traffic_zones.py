"""
Live Traffic Zone Clustering Test Suite

Verifies:
  1. Valid traffic snapshot
  2. Empty traffic snapshot
  3. Provider unavailable
  4. Spatial filtering (within selected radius)
  5. Traffic similarity (difference <= TRAFFIC_SIMILARITY_THRESHOLD)
  6. Zone clustering using DBSCAN
  7. High/medium/low zone level thresholds
  8. Zone stability (reusing zone IDs across updates)
  9. Selected-area isolation (decoupled from local browser/simulation state)
  10. Cache behavior / Registry tracking
  11. No fake data or probe generation
  12. Independent traffic/zone pipeline (no RouteFlow route impacts)
"""
import unittest
import time
from unittest.mock import patch
from app import create_app
from app.modules.live_clustering.zone_clustering_service import (
    zone_clustering_service,
    ZONE_CLUSTER_DISTANCE_METERS,
    TRAFFIC_SIMILARITY_THRESHOLD
)

class LiveTrafficZonesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def setUp(self):
        zone_clustering_service.reset()

    def tearDown(self):
        zone_clustering_service.reset()

    def test_01_valid_traffic_snapshot_clustering(self):
        """TEST 1: Valid traffic snapshot returns correctly structured zones."""
        # 4 nearby segments in Koramangala
        segments = [
            {
                "segment_id": "seg1",
                "latitude": 12.9352,
                "longitude": 77.6244,
                "current_speed_kmh": 20.0,
                "free_flow_speed_kmh": 40.0,
            },
            {
                "segment_id": "seg2",
                "latitude": 12.9353,
                "longitude": 77.6245,
                "current_speed_kmh": 22.0,
                "free_flow_speed_kmh": 40.0,
            },
            {
                "segment_id": "seg3",
                "latitude": 12.9351,
                "longitude": 77.6243,
                "current_speed_kmh": 21.0,
                "free_flow_speed_kmh": 40.0,
            },
            {
                "segment_id": "seg4",
                "latitude": 12.9380,  # Far away segment
                "longitude": 77.6300,
                "current_speed_kmh": 38.0,
                "free_flow_speed_kmh": 40.0,
            }
        ]

        # Call clustering service directly
        res = zone_clustering_service.compute_zones(segments, 12.9352, 77.6244, 1000.0)
        
        self.assertEqual(res["status"], "ACTIVE")
        self.assertEqual(res["count"], 1)  # seg1, seg2, seg3 should form 1 zone
        self.assertEqual(len(res["zones"]), 1)
        
        zone = res["zones"][0]
        self.assertEqual(zone["segment_count"], 3)
        self.assertIn("seg1", zone["segment_ids"])
        self.assertIn("seg2", zone["segment_ids"])
        self.assertIn("seg3", zone["segment_ids"])
        self.assertNotIn("seg4", zone["segment_ids"])
        self.assertEqual(zone["traffic_level"], "MEDIUM")  # avg speed = 21, ff = 40 -> cong = 0.475 (MEDIUM)

    def test_02_empty_traffic_snapshot(self):
        """TEST 2: Empty traffic snapshot returns INACTIVE status and zero zones."""
        res = zone_clustering_service.compute_zones([], 12.9352, 77.6244, 1000.0)
        self.assertEqual(res["status"], "INACTIVE")
        self.assertEqual(res["count"], 0)
        self.assertEqual(res["zones"], [])

    @patch("app.modules.live_clustering.routes.get_area_traffic")
    def test_03_provider_unavailable(self, mock_get_area_traffic):
        """TEST 3: Provider unavailable results in UNAVAILABLE status at API level."""
        mock_get_area_traffic.return_value = {
            "source": "REAL_TRAFFIC_PROVIDER",
            "status": "UNAVAILABLE",
            "provider": "ERROR",
            "provider_status": "UNAVAILABLE",
            "segments": []
        }

        res = self.client.post("/api/live-clustering/area-snapshot", json={
            "latitude": 12.9352,
            "longitude": 77.6244,
            "radius_m": 1000
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "UNAVAILABLE")
        self.assertEqual(data["zones"]["status"], "INACTIVE")

    def test_04_spatial_filtering(self):
        """TEST 4: Spatial filtering excludes segments outside the search radius."""
        segments = [
            {
                "segment_id": "near1",
                "latitude": 12.9352,
                "longitude": 77.6244,
                "current_speed_kmh": 20.0,
                "free_flow_speed_kmh": 40.0,
            },
            {
                "segment_id": "near2",
                "latitude": 12.9353,
                "longitude": 77.6245,
                "current_speed_kmh": 20.0,
                "free_flow_speed_kmh": 40.0,
            },
            {
                "segment_id": "far1",
                "latitude": 12.9900,  # ~6.5 km away
                "longitude": 77.6500,
                "current_speed_kmh": 20.0,
                "free_flow_speed_kmh": 40.0,
            }
        ]
        
        # Test with 1000m radius
        res = zone_clustering_service.compute_zones(segments, 12.9352, 77.6244, 1000.0)
        self.assertEqual(res["count"], 1)
        self.assertEqual(res["zones"][0]["segment_count"], 2)
        self.assertNotIn("far1", res["zones"][0]["segment_ids"])

    def test_05_traffic_similarity(self):
        """TEST 5: Segments with dissimilar traffic conditions are not clustered."""
        # 3 nearby segments
        segments = [
            {
                "segment_id": "low_cong",
                "latitude": 12.9352,
                "longitude": 77.6244,
                "current_speed_kmh": 38.0,  # speed ratio 0.95 (congestion 0.05)
                "free_flow_speed_kmh": 40.0,
            },
            {
                "segment_id": "high_cong1",
                "latitude": 12.9353,
                "longitude": 77.6245,
                "current_speed_kmh": 10.0,  # speed ratio 0.25 (congestion 0.75)
                "free_flow_speed_kmh": 40.0,
            },
            {
                "segment_id": "high_cong2",
                "latitude": 12.9351,
                "longitude": 77.6243,
                "current_speed_kmh": 11.0,  # speed ratio 0.275 (congestion 0.725)
                "free_flow_speed_kmh": 40.0,
            }
        ]
        
        res = zone_clustering_service.compute_zones(segments, 12.9352, 77.6244, 1000.0)
        self.assertEqual(res["count"], 1)
        zone = res["zones"][0]
        # Only high_cong1 and high_cong2 should cluster together (similar speed ratio and close)
        self.assertEqual(zone["segment_count"], 2)
        self.assertIn("high_cong1", zone["segment_ids"])
        self.assertIn("high_cong2", zone["segment_ids"])
        self.assertNotIn("low_cong", zone["segment_ids"])

    def test_06_zone_clustering_dbscan(self):
        """TEST 6: Standard DBSCAN spatial-and-traffic clustering works properly."""
        # Cluster A
        segments = [
            {"segment_id": "a1", "latitude": 12.9100, "longitude": 77.6100, "current_speed_kmh": 10.0, "free_flow_speed_kmh": 40.0},
            {"segment_id": "a2", "latitude": 12.9101, "longitude": 77.6101, "current_speed_kmh": 11.0, "free_flow_speed_kmh": 40.0},
            # Cluster B - far from A, similar speeds
            {"segment_id": "b1", "latitude": 12.9150, "longitude": 77.6150, "current_speed_kmh": 10.0, "free_flow_speed_kmh": 40.0},
            {"segment_id": "b2", "latitude": 12.9151, "longitude": 77.6151, "current_speed_kmh": 11.0, "free_flow_speed_kmh": 40.0},
        ]
        res = zone_clustering_service.compute_zones(segments, 12.9100, 77.6100, 2000.0)
        self.assertEqual(res["count"], 2)
        zone_ids = [z["zone_id"] for z in res["zones"]]
        self.assertEqual(len(zone_ids), 2)

    def test_07_traffic_level_thresholds(self):
        """TEST 7: Traffic levels are correctly classified as LOW, MEDIUM, or HIGH."""
        # Case A: LOW Congestion (congestion < 0.33)
        segs_low = [
            {"segment_id": "l1", "latitude": 12.9, "longitude": 77.6, "current_speed_kmh": 35.0, "free_flow_speed_kmh": 40.0},
            {"segment_id": "l2", "latitude": 12.9, "longitude": 77.6, "current_speed_kmh": 36.0, "free_flow_speed_kmh": 40.0},
        ]
        res_low = zone_clustering_service.compute_zones(segs_low, 12.9, 77.6, 1000)
        self.assertEqual(res_low["zones"][0]["traffic_level"], "LOW")

        # Case B: MEDIUM Congestion (0.33 <= congestion < 0.66)
        zone_clustering_service.reset()
        segs_med = [
            {"segment_id": "m1", "latitude": 12.9, "longitude": 77.6, "current_speed_kmh": 20.0, "free_flow_speed_kmh": 40.0},
            {"segment_id": "m2", "latitude": 12.9, "longitude": 77.6, "current_speed_kmh": 21.0, "free_flow_speed_kmh": 40.0},
        ]
        res_med = zone_clustering_service.compute_zones(segs_med, 12.9, 77.6, 1000)
        self.assertEqual(res_med["zones"][0]["traffic_level"], "MEDIUM")

        # Case C: HIGH Congestion (congestion >= 0.66)
        zone_clustering_service.reset()
        segs_high = [
            {"segment_id": "h1", "latitude": 12.9, "longitude": 77.6, "current_speed_kmh": 5.0, "free_flow_speed_kmh": 40.0},
            {"segment_id": "h2", "latitude": 12.9, "longitude": 77.6, "current_speed_kmh": 6.0, "free_flow_speed_kmh": 40.0},
        ]
        res_high = zone_clustering_service.compute_zones(segs_high, 12.9, 77.6, 1000)
        self.assertEqual(res_high["zones"][0]["traffic_level"], "HIGH")

    def test_08_zone_stability(self):
        """TEST 8: Reuses previous zone IDs if the segment membership persists."""
        segments_t1 = [
            {"segment_id": "s1", "latitude": 12.91, "longitude": 77.61, "current_speed_kmh": 10.0, "free_flow_speed_kmh": 40.0},
            {"segment_id": "s2", "latitude": 12.91, "longitude": 77.61, "current_speed_kmh": 10.0, "free_flow_speed_kmh": 40.0},
        ]
        res1 = zone_clustering_service.compute_zones(segments_t1, 12.91, 77.61, 1000)
        zone_id_t1 = res1["zones"][0]["zone_id"]

        # Run again with same segments
        res2 = zone_clustering_service.compute_zones(segments_t1, 12.91, 77.61, 1000)
        zone_id_t2 = res2["zones"][0]["zone_id"]

        self.assertEqual(zone_id_t1, zone_id_t2)

        # Run with overlapping segment membership
        segments_t3 = [
            {"segment_id": "s1", "latitude": 12.91, "longitude": 77.61, "current_speed_kmh": 10.0, "free_flow_speed_kmh": 40.0},
            {"segment_id": "s3", "latitude": 12.91, "longitude": 77.61, "current_speed_kmh": 10.0, "free_flow_speed_kmh": 40.0},
        ]
        res3 = zone_clustering_service.compute_zones(segments_t3, 12.91, 77.61, 1000)
        zone_id_t3 = res3["zones"][0]["zone_id"]
        self.assertEqual(zone_id_t1, zone_id_t3)

    def test_09_selected_area_isolation(self):
        """TEST 9: Selected area query isolates clustering to the defined boundary."""
        # Verify call with explicit parameters does not touch any global simulation state
        res = self.client.post("/api/live-clustering/area-snapshot", json={
            "latitude": 12.9166,
            "longitude": 77.6101,
            "radius_m": 1000,
            "name": "BTM Layout"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["area"]["name"], "BTM Layout")
        self.assertNotIn("fake_users", data)

    def test_10_cache_behavior_and_registry(self):
        """TEST 10: Zone registry maintains previous entries and resets correctly."""
        segments = [
            {"segment_id": "s1", "latitude": 12.91, "longitude": 77.61, "current_speed_kmh": 10.0, "free_flow_speed_kmh": 40.0},
            {"segment_id": "s2", "latitude": 12.91, "longitude": 77.61, "current_speed_kmh": 10.0, "free_flow_speed_kmh": 40.0},
        ]
        zone_clustering_service.compute_zones(segments, 12.91, 77.61, 1000)
        self.assertGreater(len(zone_clustering_service._previous_zones), 0)

        zone_clustering_service.reset()
        self.assertEqual(len(zone_clustering_service._previous_zones), 0)
        self.assertEqual(zone_clustering_service._zone_counter, 0)

    @patch("app.modules.live_clustering.routes.get_area_traffic")
    def test_11_no_fake_data(self, mock_get_area_traffic):
        """TEST 11: System does not generate fake zones or simulated traffic probes."""
        # Empty segments
        mock_get_area_traffic.return_value = {
            "source": "REAL_TRAFFIC_PROVIDER",
            "status": "LIVE",
            "provider": "REAL",
            "provider_status": "LIVE",
            "segments": []
        }
        res = self.client.post("/api/live-clustering/area-snapshot", json={
            "latitude": 12.91,
            "longitude": 77.61,
            "radius_m": 1000
        })
        data = res.get_json()
        self.assertEqual(data["status"], "NO_DATA")
        self.assertEqual(data["zones"]["count"], 0)
        self.assertEqual(data["zone_data"], [])

    def test_12_independent_pipeline(self):
        """TEST 12: Live Traffic Clustering is completely isolated from routing models."""
        from app.services.routing_service import routing_service
        from app.modules.road_network.services.graph_service import graph_service
        # Verify routing calculations still work completely independently
        nx_g = graph_service.get_nx_graph()
        if nx_g is None or len(nx_g.nodes()) < 2:
            import networkx as nx
            g = nx.MultiDiGraph()
            g.add_node("1", lat=12.9716, lon=77.5946)
            g.add_node("2", lat=12.9720, lon=77.5950)
            g.add_edge("1", "2", key=0, length=100.0, weight=100.0)
            graph_service._nx_graph = g
            nx_g = g
        self.assertIsNotNone(nx_g)
        nodes = list(nx_g.nodes())
        self.assertGreaterEqual(len(nodes), 2)
        res = routing_service.calculate_route(
            source_node=nodes[0],
            destination_node=nodes[1],
            algorithm="astar"
        )
        self.assertIsNotNone(res)



if __name__ == "__main__":
    unittest.main()
