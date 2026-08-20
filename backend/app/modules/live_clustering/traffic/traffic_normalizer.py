"""
Live Clustering — Traffic Normalizer (Segment Mapper)
"""
import os
import math
import logging
from typing import Dict, Any, List, Optional, Tuple

from app.modules.road_network.services.graph_service import graph_service
from .traffic_cache import mapping_cache
from ..config import TRAFFIC_EDGE_MATCH_DISTANCE_METERS

logger = logging.getLogger("routeflow.live_clustering.traffic_normalizer")


def _point_to_line_segment_distance_m(
    p_lat: float, p_lon: float,
    a_lat: float, a_lon: float,
    b_lat: float, b_lon: float
) -> float:
    lat_rad = math.radians(p_lat)
    cos_lat = math.cos(lat_rad)
    m_per_deg_lat = 111132.92
    m_per_deg_lon = 111412.84 * cos_lat

    px, py = 0.0, 0.0
    ax = (a_lon - p_lon) * m_per_deg_lon
    ay = (a_lat - p_lat) * m_per_deg_lat
    bx = (b_lon - p_lon) * m_per_deg_lon
    by = (b_lat - p_lat) * m_per_deg_lat

    abx = bx - ax
    aby = by - ay
    ab_sq = abx * abx + aby * aby

    if ab_sq == 0.0:
        return math.hypot(ax, ay)

    apx = px - ax
    apy = py - ay
    t = (apx * abx + apy * aby) / ab_sq
    t = max(0.0, min(1.0, t))

    nx = ax + t * abx
    ny = ay + t * aby

    return math.hypot(nx, ny)


def map_segment(segment: Dict[str, Any]) -> Dict[str, Any]:
    seg_id = str(segment.get("segment_id", "unknown_seg"))
    lat = segment.get("latitude")
    lon = segment.get("longitude")

    if lat is None or lon is None:
        return {
            "external_segment_id": seg_id,
            "routeflow_edge_id": None,
            "matched": False,
            "reason": "MISSING_COORDINATES",
            "match_distance_meters": None,
            "match_confidence": "NONE",
            "latitude": lat,
            "longitude": lon,
            "current_speed_kmh": segment.get("current_speed_kmh"),
            "free_flow_speed_kmh": segment.get("free_flow_speed_kmh"),
            "congestion_level": segment.get("congestion_level"),
            "traffic_status": segment.get("status", "UNAVAILABLE"),
            "color": segment.get("color", "#94a3b8"),
            "timestamp": segment.get("timestamp"),
        }

    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return {
            "external_segment_id": seg_id,
            "routeflow_edge_id": None,
            "matched": False,
            "reason": "INVALID_COORDINATES",
            "match_distance_meters": None,
            "match_confidence": "NONE",
            "latitude": lat,
            "longitude": lon,
            "current_speed_kmh": segment.get("current_speed_kmh"),
            "free_flow_speed_kmh": segment.get("free_flow_speed_kmh"),
            "congestion_level": segment.get("congestion_level"),
            "traffic_status": segment.get("status", "UNAVAILABLE"),
            "color": segment.get("color", "#94a3b8"),
            "timestamp": segment.get("timestamp"),
        }

    cached = mapping_cache.get(seg_id, lat, lon)
    if cached is not None:
        return cached

    try:
        nx_g = graph_service.ensure_graph_for_points(lat, lon)
    except Exception as exc:
        logger.warning("[SegmentMapper] Could not load graph: %s", exc)
        nx_g = None

    if nx_g is None or len(nx_g) == 0:
        res = {
            "external_segment_id": seg_id,
            "routeflow_edge_id": None,
            "matched": False,
            "reason": "GRAPH_UNAVAILABLE",
            "match_distance_meters": None,
            "match_confidence": "NONE",
            "latitude": lat,
            "longitude": lon,
            "current_speed_kmh": segment.get("current_speed_kmh"),
            "free_flow_speed_kmh": segment.get("free_flow_speed_kmh"),
            "congestion_level": segment.get("congestion_level"),
            "traffic_status": segment.get("status", "UNAVAILABLE"),
            "color": segment.get("color", "#94a3b8"),
            "timestamp": segment.get("timestamp"),
        }
        mapping_cache.set(seg_id, lat, lon, res)
        return res

    candidates = graph_service.find_candidates_in_radius(lat, lon, radius_km=0.20)
    if not candidates:
        fast_node = graph_service.find_nearest_node_fast(lat, lon)
        if fast_node:
            candidates = [fast_node]

    if not candidates:
        res = {
            "external_segment_id": seg_id,
            "routeflow_edge_id": None,
            "matched": False,
            "reason": "NO_ROAD_CANDIDATES",
            "match_distance_meters": None,
            "match_confidence": "NONE",
            "latitude": lat,
            "longitude": lon,
            "current_speed_kmh": segment.get("current_speed_kmh"),
            "free_flow_speed_kmh": segment.get("free_flow_speed_kmh"),
            "congestion_level": segment.get("congestion_level"),
            "traffic_status": segment.get("status", "UNAVAILABLE"),
            "color": segment.get("color", "#94a3b8"),
            "timestamp": segment.get("timestamp"),
        }
        mapping_cache.set(seg_id, lat, lon, res)
        return res

    best_dist_m = float("inf")
    best_edge_id = None
    best_edge_data = None
    best_geometry = None

    checked_edges = set()

    for cand in candidates:
        node_id = cand["node_id"]
        if nx_g.has_node(node_id):
            out_edges = nx_g.out_edges(node_id, data=True)
            in_edges = nx_g.in_edges(node_id, data=True)
            all_edges = list(out_edges) + list(in_edges)

            for u, v, data in all_edges:
                edge_key = (u, v)
                if edge_key in checked_edges:
                    continue
                checked_edges.add(edge_key)

                u_data = nx_g.nodes.get(u, {})
                v_data = nx_g.nodes.get(v, {})

                u_lat = u_data.get("lat", u_data.get("y"))
                u_lon = u_data.get("lon", u_data.get("x"))
                v_lat = v_data.get("lat", v_data.get("y"))
                v_lon = v_data.get("lon", v_data.get("x"))

                if u_lat is None or u_lon is None or v_lat is None or v_lon is None:
                    continue

                dist_m = _point_to_line_segment_distance_m(
                    lat, lon, float(u_lat), float(u_lon), float(v_lat), float(v_lon)
                )

                if dist_m < best_dist_m:
                    best_dist_m = dist_m
                    best_edge_id = f"{u}_{v}"
                    best_edge_data = data
                    best_geometry = [[float(u_lat), float(u_lon)], [float(v_lat), float(v_lon)]]

    if best_edge_id is not None and best_dist_m <= TRAFFIC_EDGE_MATCH_DISTANCE_METERS:
        if best_dist_m <= 15.0:
            confidence = "HIGH"
        elif best_dist_m <= 35.0:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        res = {
            "external_segment_id": seg_id,
            "routeflow_edge_id": best_edge_id,
            "matched": True,
            "match_distance_meters": round(best_dist_m, 1),
            "match_confidence": confidence,
            "edge_name": best_edge_data.get("name", "Bengaluru Road Segment"),
            "edge_geometry": best_geometry,
            "latitude": lat,
            "longitude": lon,
            "current_speed_kmh": segment.get("current_speed_kmh"),
            "free_flow_speed_kmh": segment.get("free_flow_speed_kmh"),
            "congestion_level": segment.get("congestion_level"),
            "traffic_status": segment.get("status", "UNAVAILABLE"),
            "color": segment.get("color", "#f59e0b"),
            "timestamp": segment.get("timestamp"),
        }
    else:
        res = {
            "external_segment_id": seg_id,
            "routeflow_edge_id": None,
            "matched": False,
            "reason": "EXCEEDS_DISTANCE_THRESHOLD" if best_dist_m != float("inf") else "NO_MATCH",
            "match_distance_meters": round(best_dist_m, 1) if best_dist_m != float("inf") else None,
            "match_confidence": "NONE",
            "latitude": lat,
            "longitude": lon,
            "current_speed_kmh": segment.get("current_speed_kmh"),
            "free_flow_speed_kmh": segment.get("free_flow_speed_kmh"),
            "congestion_level": segment.get("congestion_level"),
            "traffic_status": segment.get("status", "UNAVAILABLE"),
            "color": segment.get("color", "#94a3b8"),
            "timestamp": segment.get("timestamp"),
        }

    mapping_cache.set(seg_id, lat, lon, res)
    return res


def map_traffic_payload(traffic_payload: Dict[str, Any]) -> Dict[str, Any]:
    raw_segments = traffic_payload.get("segments", [])
    if not raw_segments:
        result = dict(traffic_payload)
        result["segments"] = []
        result["mapping_summary"] = {
            "total_segments": 0,
            "matched_count": 0,
            "unmatched_count": 0,
            "match_percentage": 0.0,
        }
        return result

    mapped_segments = []
    matched_cnt = 0

    for seg in raw_segments:
        m = map_segment(seg)
        mapped_segments.append(m)
        if m.get("matched"):
            matched_cnt += 1

    total_cnt = len(mapped_segments)
    unmatched_cnt = total_cnt - matched_cnt
    match_pct = round((matched_cnt / total_cnt) * 100.0, 1) if total_cnt > 0 else 0.0

    result = dict(traffic_payload)
    result["segments"] = mapped_segments
    result["mapping_summary"] = {
        "total_segments": total_cnt,
        "matched_count": matched_cnt,
        "unmatched_count": unmatched_cnt,
        "match_percentage": match_pct,
    }
    return result
