"""
Live Traffic Zone Clustering Service

Groups nearby road segments with similar traffic conditions into Traffic Zones
using DBSCAN clustering.
"""
import os
import math
import logging
import threading
import time
from typing import Dict, List, Any, Set, Optional, Tuple
import numpy as np
from sklearn.cluster import DBSCAN

logger = logging.getLogger("routeflow.live_clustering.zone_clustering_service")

# --------------------------------------------------------------------------- #
# Configuration values (customizable via env variables)
# --------------------------------------------------------------------------- #
ZONE_CLUSTER_DISTANCE_METERS: float = float(os.environ.get("ZONE_CLUSTER_DISTANCE_METERS", 150.0))
TRAFFIC_SIMILARITY_THRESHOLD: float = float(os.environ.get("TRAFFIC_SIMILARITY_THRESHOLD", 0.25))
MIN_SEGMENTS_PER_ZONE: int = int(os.environ.get("MIN_SEGMENTS_PER_ZONE", 2))

ZONE_CONGESTION_LOW_THRESHOLD: float = float(os.environ.get("ZONE_CONGESTION_LOW_THRESHOLD", 0.33))
ZONE_CONGESTION_HIGH_THRESHOLD: float = float(os.environ.get("ZONE_CONGESTION_HIGH_THRESHOLD", 0.66))


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points in meters."""
    R = 6371000.0  # Earth's radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return R * c


class ZoneClusteringService:
    """
    Service for spatial and traffic-state similarity segment clustering.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._zone_counter = 0
        # Active zone identity registry: zone_id -> Dict
        self._previous_zones: Dict[str, Dict[str, Any]] = {}

    def _generate_zone_id(self) -> str:
        """Generates sequential zone identifier."""
        self._zone_counter += 1
        return f"zone_{self._zone_counter:02d}"

    def reset(self) -> None:
        """Resets the zone ID generator and tracking cache."""
        with self._lock:
            self._previous_zones.clear()
            self._zone_counter = 0

    def compute_zones(
        self,
        segments: List[Dict[str, Any]],
        center_lat: float,
        center_lon: float,
        radius_m: float
    ) -> Dict[str, Any]:
        """
        Groups traffic segments into zones using DBSCAN with a custom distance matrix.
        Only segments within the selected area/radius are clustered.
        """
        with self._lock:
            # 1. Filter segments to the selected area radius
            area_segments = []
            for seg in segments:
                lat = seg.get("latitude")
                lon = seg.get("longitude")
                if lat is not None and lon is not None:
                    dist = haversine_distance_meters(center_lat, center_lon, lat, lon)
                    if dist <= radius_m:
                        area_segments.append(seg)

            if not area_segments:
                self._previous_zones.clear()
                return {
                    "status": "INACTIVE",
                    "count": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                    "zones": [],
                }

            # 2. Build custom distance matrix D
            # If distance > ZONE_CLUSTER_DISTANCE_METERS or traffic speed ratio diff > threshold,
            # D[i][j] = 999999.0 (exceeding eps). Else D[i][j] = geographic distance in meters.
            n = len(area_segments)
            D = np.zeros((n, n))

            for i in range(n):
                seg_i = area_segments[i]
                lat_i = float(seg_i["latitude"])
                lon_i = float(seg_i["longitude"])

                # Compute speed ratio (defaulting to 1.0 if missing or invalid)
                try:
                    speed_i = float(seg_i.get("current_speed_kmh", 0))
                    ff_i = float(seg_i.get("free_flow_speed_kmh", 0))
                    ratio_i = speed_i / ff_i if ff_i > 0 else 1.0
                except (ValueError, TypeError, ZeroDivisionError):
                    ratio_i = 1.0

                for j in range(i, n):
                    if i == j:
                        D[i][j] = 0.0
                        continue

                    seg_j = area_segments[j]
                    lat_j = float(seg_j["latitude"])
                    lon_j = float(seg_j["longitude"])

                    try:
                        speed_j = float(seg_j.get("current_speed_kmh", 0))
                        ff_j = float(seg_j.get("free_flow_speed_kmh", 0))
                        ratio_j = speed_j / ff_j if ff_j > 0 else 1.0
                    except (ValueError, TypeError, ZeroDivisionError):
                        ratio_j = 1.0

                    geo_dist = haversine_distance_meters(lat_i, lon_i, lat_j, lon_j)
                    ratio_diff = abs(ratio_i - ratio_j)

                    if (
                        geo_dist > ZONE_CLUSTER_DISTANCE_METERS
                        or ratio_diff > TRAFFIC_SIMILARITY_THRESHOLD
                    ):
                        D[i][j] = 999999.0
                        D[j][i] = 999999.0
                    else:
                        D[i][j] = geo_dist
                        D[j][i] = geo_dist

            # 3. Run DBSCAN on the precomputed distance matrix
            # Use eps = ZONE_CLUSTER_DISTANCE_METERS
            db = DBSCAN(
                metric="precomputed",
                eps=ZONE_CLUSTER_DISTANCE_METERS,
                min_samples=MIN_SEGMENTS_PER_ZONE
            )
            labels = db.fit_predict(D)

            # 4. Group segments by label
            clusters: Dict[int, List[Dict[str, Any]]] = {}
            for idx, label in enumerate(labels):
                if label == -1:
                    continue  # Noise
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(area_segments[idx])

            # 5. Build zone objects with ID stability
            new_zones: List[Dict[str, Any]] = []
            updated_prev_zones: Dict[str, Dict[str, Any]] = {}
            now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            for label, cluster_segs in clusters.items():
                seg_ids = sorted([str(s.get("segment_id")) for s in cluster_segs])
                avg_lat = sum(float(s["latitude"]) for s in cluster_segs) / len(cluster_segs)
                avg_lon = sum(float(s["longitude"]) for s in cluster_segs) / len(cluster_segs)

                # Speeds
                speeds = [float(s["current_speed_kmh"]) for s in cluster_segs if s.get("current_speed_kmh") is not None]
                ff_speeds = [float(s["free_flow_speed_kmh"]) for s in cluster_segs if s.get("free_flow_speed_kmh") is not None]

                avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
                avg_ff = sum(ff_speeds) / len(ff_speeds) if ff_speeds else 0.0

                # Compute congestion ratio: 1.0 - (avg_speed / avg_ff)
                if avg_ff > 0.0:
                    avg_congestion = max(0.0, min(1.0, 1.0 - (avg_speed / avg_ff)))
                else:
                    avg_congestion = 0.0

                min_speed = min(speeds) if speeds else 0.0
                max_speed = max(speeds) if speeds else 0.0

                # Resolve Zone Traffic Level
                if avg_congestion < ZONE_CONGESTION_LOW_THRESHOLD:
                    traffic_level = "LOW"
                elif avg_congestion < ZONE_CONGESTION_HIGH_THRESHOLD:
                    traffic_level = "MEDIUM"
                else:
                    traffic_level = "HIGH"

                # Stability matching
                matched_id = self._match_zone_id(seg_ids, avg_lat, avg_lon)
                if not matched_id:
                    matched_id = self._generate_zone_id()
                    created_at = now_iso
                else:
                    created_at = self._previous_zones[matched_id].get("created_at", now_iso)

                zone_obj = {
                    "zone_id": matched_id,
                    "segment_ids": seg_ids,
                    "center_latitude": round(avg_lat, 6),
                    "center_longitude": round(avg_lon, 6),
                    "segment_count": len(cluster_segs),
                    "traffic_level": traffic_level,
                    "average_speed_kmh": round(avg_speed, 1),
                    "average_free_flow_speed_kmh": round(avg_ff, 1),
                    "average_congestion_ratio": round(avg_congestion, 2),
                    "min_speed_kmh": round(min_speed, 1),
                    "max_speed_kmh": round(max_speed, 1),
                    "created_at": created_at,
                    "last_updated": now_iso,
                }
                new_zones.append(zone_obj)
                updated_prev_zones[matched_id] = zone_obj

            self._previous_zones = updated_prev_zones

            # 6. Compute top-level counts
            high_count = sum(1 for z in new_zones if z["traffic_level"] == "HIGH")
            medium_count = sum(1 for z in new_zones if z["traffic_level"] == "MEDIUM")
            low_count = sum(1 for z in new_zones if z["traffic_level"] == "LOW")

            return {
                "status": "ACTIVE",
                "count": len(new_zones),
                "high": high_count,
                "medium": medium_count,
                "low": low_count,
                "zones": new_zones,
            }

    def _match_zone_id(self, segment_ids: List[str], center_lat: float, center_lon: float) -> Optional[str]:
        """
        Attempts to match a new zone to a previous zone to preserve the zone ID.
        Uses Jaccard overlap on segment IDs first, falling back to spatial proximity.
        """
        new_set = set(segment_ids)
        best_id = None
        best_jaccard = 0.0
        min_dist = float("inf")

        for zid, prev_zone in self._previous_zones.items():
            prev_set = set(prev_zone.get("segment_ids", []))
            intersection = new_set.intersection(prev_set)
            union = new_set.union(prev_set)

            if union:
                jaccard = len(intersection) / len(union)
                if jaccard > best_jaccard:
                    best_jaccard = jaccard
                    best_id = zid

            # Center distance fallback if no Jaccard overlap
            if best_jaccard == 0.0:
                dist = haversine_distance_meters(
                    center_lat,
                    center_lon,
                    prev_zone["center_latitude"],
                    prev_zone["center_longitude"]
                )
                if dist <= ZONE_CLUSTER_DISTANCE_METERS and dist < min_dist:
                    min_dist = dist
                    best_id = zid

        # Allow match if there is any Jaccard overlap or within spatial threshold
        if best_jaccard > 0.0 or min_dist <= ZONE_CLUSTER_DISTANCE_METERS:
            return best_id
        return None


# Module-level singleton
zone_clustering_service = ZoneClusteringService()
