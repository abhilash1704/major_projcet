import re
import logging
import requests
from flask import current_app
from ..constants import OSM_PROVIDER_DEFAULT_URL, DEFAULT_GEO_BOUNDS, DEFAULT_SPEED_LIMITS
from ..models import RoadNode, RoadEdge
from ..utils.geo_utils import haversine_distance, calculate_travel_time, is_valid_coordinate

def parse_speed_limit(maxspeed_str, default_speed=40.0):
    """Safely extracts numeric km/h speed limit from OSM maxspeed strings like '50', '30 mph', 'IN:urban'."""
    if maxspeed_str is None:
        return float(default_speed)
    if isinstance(maxspeed_str, (int, float)):
        return float(maxspeed_str)

    s = str(maxspeed_str).strip().lower()
    is_mph = 'mph' in s
    match = re.search(r'(\d+(?:\.\d+)?)', s)
    if match:
        val = float(match.group(1))
        if is_mph:
            val = val * 1.60934
        return round(val, 1)
    return float(default_speed)

class OSMService:
    """
    Service responsible for OpenStreetMap road network data retrieval and parsing.
    Queries Overpass API or generates fallback synthetic road networks when offline.
    """
    def __init__(self, provider_url=None):
        self.provider_url = provider_url or OSM_PROVIDER_DEFAULT_URL

    def _get_logger(self):
        try:
            if current_app and hasattr(current_app, 'logger') and current_app.logger:
                return current_app.logger
        except Exception:
            pass
        return logging.getLogger("routeflow.road_network.osm")

    def fetch_road_data(self, bbox=None):
        """
        Retrieves raw OpenStreetMap road data for a bounding box via Overpass API.
        Falls back gracefully to synthetic dataset if network is unavailable or rate-limited.
        """
        logger = self._get_logger()
        target_bbox = bbox or DEFAULT_GEO_BOUNDS

        min_lat = target_bbox.get('min_lat', 12.8000)
        max_lat = target_bbox.get('max_lat', 13.1500)
        min_lng = target_bbox.get('min_lng', 77.4000)
        max_lng = target_bbox.get('max_lng', 77.7500)

        logger.info("Loading road network data for bbox: %s using provider %s", target_bbox, self.provider_url)

        overpass_query = f"""
        [out:json][timeout:90];
        (
          way["highway"~"motorway|trunk|primary|secondary|tertiary|residential|unclassified"]({min_lat},{min_lng},{max_lat},{max_lng});
        );
        out body;
        >;
        out skel qt;
        """

        try:
            response = requests.post(
                self.provider_url,
                data={'data': overpass_query},
                headers={'User-Agent': 'RouteFlow-NavigationEngine/1.0'},
                timeout=45
            )

            if response.status_code == 200:
                data = response.json()
                elements = data.get('elements', [])
                if elements:
                    logger.info("Successfully fetched %d OSM elements from Overpass API", len(elements))
                    return {
                        "status": "success",
                        "source": "overpass_api",
                        "provider": self.provider_url,
                        "bbox": target_bbox,
                        "elements": elements
                    }
        except Exception as e:
            logger.warning("Overpass API request failed or timed out: %s. Using fallback road network generator.", str(e))

        return self._generate_fallback_osm_data(target_bbox)

    def parse_osm_response(self, raw_data):
        """
        Parses raw OSM elements into structured RoadNode and RoadEdge model objects.
        """
        logger = self._get_logger()
        logger.info("Parsing OpenStreetMap response data")

        elements = raw_data.get('elements', []) if isinstance(raw_data, dict) else []
        nodes_dict = {}
        ways_list = []

        for elem in elements:
            if elem.get('type') == 'node':
                nid = str(elem['id'])
                lat = elem.get('lat')
                lon = elem.get('lon')
                if is_valid_coordinate(lat, lon):
                    nodes_dict[nid] = RoadNode(node_id=nid, latitude=lat, longitude=lon, tags=elem.get('tags'))

        parsed_edges = []

        for elem in elements:
            if elem.get('type') == 'way':
                tags = elem.get('tags', {})
                highway = tags.get('highway', 'default')
                road_name = tags.get('name', f"Road {elem.get('id')}")
                oneway = tags.get('oneway') in ['yes', '1', 'true']
                default_speed = DEFAULT_SPEED_LIMITS.get(highway, DEFAULT_SPEED_LIMITS['default'])
                speed_limit = parse_speed_limit(tags.get('maxspeed'), default_speed)

                way_nodes = elem.get('nodes', [])
                for i in range(len(way_nodes) - 1):
                    u_id = str(way_nodes[i])
                    v_id = str(way_nodes[i + 1])

                    if u_id in nodes_dict and v_id in nodes_dict:
                        u_node = nodes_dict[u_id]
                        v_node = nodes_dict[v_id]

                        dist_km = haversine_distance(u_node.latitude, u_node.longitude, v_node.latitude, v_node.longitude)
                        tt_sec = calculate_travel_time(dist_km, speed_limit)

                        edge_forward = RoadEdge(
                            source=u_id,
                            target=v_id,
                            distance=round(dist_km, 4),
                            road_type=highway,
                            speed_limit=speed_limit,
                            travel_time=tt_sec,
                            name=road_name,
                            oneway=oneway
                        )
                        parsed_edges.append(edge_forward)

                        if not oneway:
                            edge_reverse = RoadEdge(
                                source=v_id,
                                target=u_id,
                                distance=round(dist_km, 4),
                                road_type=highway,
                                speed_limit=speed_limit,
                                travel_time=tt_sec,
                                name=road_name,
                                oneway=oneway
                            )
                            parsed_edges.append(edge_reverse)

        # Filter nodes that are actually connected by edges
        used_node_ids = set()
        for e in parsed_edges:
            used_node_ids.add(e.source)
            used_node_ids.add(e.target)

        final_nodes = [node for nid, node in nodes_dict.items() if nid in used_node_ids]

        logger.info("OSM data parsed: %d valid connected nodes, %d directed edges", len(final_nodes), len(parsed_edges))
        return {
            "nodes": final_nodes,
            "edges": parsed_edges
        }

    def _generate_fallback_osm_data(self, bbox):
        """
        Generates a realistic synthetic road network grid around the bounding box center.
        Ensures system works reliably without external network dependencies.
        """
        logger = self._get_logger()
        logger.info("Generating synthetic fallback road network for bbox: %s", bbox)

        min_lat = bbox.get('min_lat', 12.8000)
        max_lat = bbox.get('max_lat', 13.1500)
        min_lng = bbox.get('min_lng', 77.4000)
        max_lng = bbox.get('max_lng', 77.7500)

        center_lat = (min_lat + max_lat) / 2.0
        center_lng = (min_lng + max_lng) / 2.0

        elements = []
        rows = 6
        cols = 6
        lat_step = (max_lat - min_lat) / (rows + 1)
        lng_step = (max_lng - min_lng) / (cols + 1)

        # Grid of nodes
        node_grid = {}
        node_id_counter = 1000

        for r in range(rows):
            for c in range(cols):
                nid = node_id_counter
                node_id_counter += 1
                lat = round(min_lat + (r + 1) * lat_step, 6)
                lon = round(min_lng + (c + 1) * lng_step, 6)
                node_grid[(r, c)] = nid

                elements.append({
                    "type": "node",
                    "id": nid,
                    "lat": lat,
                    "lon": lon
                })

        # Horizontal ways
        way_id_counter = 5000
        for r in range(rows):
            nodes_in_way = [node_grid[(r, c)] for c in range(cols)]
            highway_type = "primary" if r % 2 == 0 else "secondary"
            elements.append({
                "type": "way",
                "id": way_id_counter,
                "nodes": nodes_in_way,
                "tags": {
                    "highway": highway_type,
                    "name": f"Avenue {r + 1}",
                    "maxspeed": "50"
                }
            })
            way_id_counter += 1

        # Vertical ways
        for c in range(cols):
            nodes_in_way = [node_grid[(r, c)] for r in range(rows)]
            highway_type = "trunk" if c % 2 == 0 else "tertiary"
            elements.append({
                "type": "way",
                "id": way_id_counter,
                "nodes": nodes_in_way,
                "tags": {
                    "highway": highway_type,
                    "name": f"Boulevard {c + 1}",
                    "maxspeed": "60"
                }
            })
            way_id_counter += 1

        return {
            "status": "success",
            "source": "synthetic_fallback",
            "provider": self.provider_url,
            "bbox": bbox,
            "elements": elements
        }

    def health_check(self):
        return {
            "service": "osm_service",
            "provider_url": self.provider_url,
            "status": "ready"
        }

osm_service = OSMService()
