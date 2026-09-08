/**
 * LiveClusteringMap.jsx — Interactive Leaflet Map for Live Vehicle Clustering
 *
 * Primary Visualization: CLUSTERS FIRST
 * View Switcher: [ Clusters ] [ Users ] [ Density ]
 */
import {
  MapContainer, TileLayer, CircleMarker, Circle, Tooltip, Marker, Polyline, useMap, Popup
} from "react-leaflet";
import { useEffect, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useLiveClustering } from "../context/LiveClusteringContext";
import { Layers, Filter, X } from "lucide-react";

const BENGALURU_CENTER = [12.9174, 77.6228];
const TILE_URL  = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

/**
 * Clean count badge for cluster (e.g. [5])
 */
const createClusterCountIcon = (count, isSelected) => L.divIcon({
  className: "custom-cluster-badge",
  html: `<div style="
    background: ${isSelected ? "#2563eb" : "#059669"};
    color: white;
    font-weight: 800;
    font-size: 11px;
    font-family: ui-sans-serif, system-ui, sans-serif;
    padding: 2px 7px;
    border-radius: 10px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    border: 1.5px solid white;
    text-align: center;
    white-space: nowrap;
    line-height: 1.1;
    transform: translateY(-2px);
  ">[ ${count} ]</div>`,
  iconSize: [32, 22],
  iconAnchor: [16, 26],
});

const areaCenterIcon = L.divIcon({
  className: "",
  html: `<div style="
    width:18px; height:18px;
    background:linear-gradient(135deg,#2563eb,#3b82f6);
    border:2px solid #fff;
    border-radius:50% 50% 50% 0;
    transform:rotate(-45deg);
    box-shadow:0 2px 5px rgba(37,99,235,0.4);
  "></div>`,
  iconSize:   [18, 18],
  iconAnchor: [9, 18],
});

const FlyToArea = ({ area, radius }) => {
  const map = useMap();
  useEffect(() => {
    if (area && typeof area.latitude === "number" && typeof area.longitude === "number") {
      const zoom = radius <= 500 ? 15 : radius <= 1000 ? 14 : 13;
      map.invalidateSize();
      map.setView([area.latitude, area.longitude], zoom, { animate: true });
    }
  }, [area?.latitude, area?.longitude, radius, map]);
  return null;
};

const MapZoomTracker = ({ onZoomChange }) => {
  const map = useMap();
  useEffect(() => {
    const handleZoom = () => onZoomChange(map.getZoom());
    map.on("zoomend", handleZoom);
    return () => map.off("zoomend", handleZoom);
  }, [map, onZoomChange]);
  return null;
};

const getSegmentCenter = (seg) => {
  if (typeof seg.latitude === "number" && typeof seg.longitude === "number") {
    return [seg.latitude, seg.longitude];
  }
  if (typeof seg.center_lat === "number" && typeof seg.center_lng === "number") {
    return [seg.center_lat, seg.center_lng];
  }
  const coords = seg.geometry || seg.coordinates;
  if (Array.isArray(coords) && coords.length > 0) {
    const midPoint = coords[Math.floor(coords.length / 2)];
    if (Array.isArray(midPoint) && midPoint.length >= 2) {
      return [midPoint[0], midPoint[1]];
    }
  }
  return null;
};

// Client-side Haversine distance safety check
const haversineMeters = (lat1, lon1, lat2, lon2) => {
  const R = 6371000;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(Math.max(0, 1 - a)));
};

export const LiveClusteringMap = () => {
  const {
    selectedArea,
    analysisRadiusMeters,
    observations,
    clustering,
    roadDensity,
    selectedCluster,
    setSelectedCluster,
    selectedSegment,
    setSelectedSegment,
    selectedDensityFilter,
    clearDensityFilter,
  } = useLiveClustering();

  const [currentZoom, setCurrentZoom] = useState(14);
  // View mode switcher: 'Clusters' (default) | 'Users' | 'Density'
  const [viewMode, setViewMode] = useState("Clusters");

  const rawClusters = clustering.clusters || [];
  const segments = roadDensity.road_segments || [];

  // Client-side safety filtering against selectedArea center and radius
  const clusters = rawClusters.filter((c) => {
    if (!c.center_latitude || !c.center_longitude || !selectedArea) return false;
    return (
      haversineMeters(
        selectedArea.latitude,
        selectedArea.longitude,
        c.center_latitude,
        c.center_longitude
      ) <= analysisRadiusMeters
    );
  });

  const validObservations = observations.filter((obs) => {
    if (!obs.latitude || !obs.longitude || !selectedArea) return false;
    return (
      haversineMeters(
        selectedArea.latitude,
        selectedArea.longitude,
        obs.latitude,
        obs.longitude
      ) <= analysisRadiusMeters
    );
  });

  const DENSITY_COLORS = {
    HIGH:   "#ef4444",
    MEDIUM: "#f59e0b",
    LOW:    "#10b981",
  };

  const activeDensitySegments = selectedDensityFilter
    ? segments.filter((seg) => (seg.density_rank || seg.density_level) === selectedDensityFilter)
    : [];

  // Opacity calculations based on View Mode
  const getObservationOpacity = () => {
    if (viewMode === "Users") return 0.85;
    if (viewMode === "Clusters") return 0.35;
    return 0.2;
  };

  const getClusterOpacity = () => {
    if (viewMode === "Clusters") return 0.95;
    if (viewMode === "Users") return 0.4;
    return 0.6;
  };

  const getRoadOpacity = (level, isSelected, isMatchingFilter) => {
    if (viewMode === "Density") {
      return isSelected ? 1.0 : (isMatchingFilter ? 0.95 : 0.7);
    }
    if (selectedDensityFilter) {
      return isMatchingFilter ? 0.9 : 0.2;
    }
    return isSelected ? 1.0 : 0.55;
  };

  return (
    <div className="w-full h-full relative flex-1 min-h-[450px]">
      
      {/* ── MAP VIEW MODE SWITCHER (Floating Top-Right) ───────────────── */}
      <div className="absolute top-4 right-4 z-[1000] bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border border-slate-200 dark:border-slate-800 rounded-lg p-1 shadow-md flex items-center gap-1 font-sans">
        <span className="text-[10px] font-bold text-slate-400 px-2 flex items-center gap-1 uppercase tracking-wider">
          <Layers className="w-3 h-3 text-blue-500" />
          View:
        </span>
        {["Clusters", "Users", "Density"].map((mode) => (
          <button
            key={mode}
            onClick={() => setViewMode(mode)}
            className={`px-2.5 py-1 text-xs font-bold rounded transition-all cursor-pointer ${
              viewMode === mode
                ? "bg-blue-600 text-white shadow-xs"
                : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
          >
            {mode}
          </button>
        ))}
      </div>

      <MapContainer
        center={selectedArea ? [selectedArea.latitude, selectedArea.longitude] : BENGALURU_CENTER}
        zoom={14}
        scrollWheelZoom
        zoomControl={false}
        className="w-full h-full z-0"
        style={{ minHeight: "450px" }}
      >
        <TileLayer url={TILE_URL} attribution={TILE_ATTR} maxZoom={19} />
        <FlyToArea area={selectedArea} radius={analysisRadiusMeters} />
        <MapZoomTracker onZoomChange={setCurrentZoom} />

        {/* ── Selected Area Boundary Circle (Subtle Dashed Blue) ─────────── */}
        {selectedArea && (
          <>
            <Circle
              center={[selectedArea.latitude, selectedArea.longitude]}
              radius={analysisRadiusMeters}
              pathOptions={{
                color:       "#2563eb",
                fillColor:   "#3b82f6",
                fillOpacity: 0.04,
                weight:      1.5,
                dashArray:   "5, 5",
              }}
            />
            <Marker
              position={[selectedArea.latitude, selectedArea.longitude]}
              icon={areaCenterIcon}
            >
              <Tooltip direction="top" offset={[0, -18]} opacity={0.95}>
                <div className="text-xs font-semibold px-1 py-0.5">
                  <div className="text-blue-700 font-bold">{selectedArea.name}</div>
                  <div className="text-slate-500 font-normal">
                    {analysisRadiusMeters >= 1000 ? `${analysisRadiusMeters / 1000} km` : `${analysisRadiusMeters} m`} analysis boundary
                  </div>
                </div>
              </Tooltip>
            </Marker>
          </>
        )}

        {/* ── Road Density Overlay Segments ──────────────────────────────── */}
        {segments.map((seg, idx) => {
          const coords = seg.geometry || seg.coordinates;
          if (!coords || coords.length < 2) return null;
          const level = seg.density_rank || seg.density_level;
          const isSelected = selectedSegment?.road_edge_id === seg.road_edge_id;
          const color = DENSITY_COLORS[level] || "#10b981";

          const isMatchingFilter = selectedDensityFilter === level;
          const polyOpacity = getRoadOpacity(level, isSelected, isMatchingFilter);

          return (
            <Polyline
              key={`road-seg-${seg.road_edge_id || idx}`}
              positions={coords}
              pathOptions={{
                color:     isSelected ? "#2563eb" : color,
                weight:    isSelected ? 7 : (viewMode === "Density" || isMatchingFilter ? 5 : 3.5),
                opacity:   polyOpacity,
              }}
              eventHandlers={{ click: () => setSelectedSegment(isSelected ? null : seg) }}
            >
              <Tooltip direction="top" opacity={0.95}>
                <div className="text-xs font-sans px-1 space-y-0.5">
                  <div className="font-bold text-slate-800 flex items-center justify-between gap-3">
                    <span>{seg.road_name || seg.road_edge_id}</span>
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded text-white" style={{ backgroundColor: color }}>
                      {level || "LOW"} DENSITY
                    </span>
                  </div>
                  <div className="text-slate-600 text-[11px]">
                    Est. Vehicles: <span className="font-bold text-slate-900">{seg.vehicle_count || 1}</span>
                  </div>
                </div>
              </Tooltip>
            </Polyline>
          );
        })}

        {/* ── Interactive Density Highlight Circles ─────────────────────── */}
        {selectedDensityFilter && activeDensitySegments.map((seg, idx) => {
          const centerPos = getSegmentCenter(seg);
          if (!centerPos) return null;
          
          const filterColor = DENSITY_COLORS[selectedDensityFilter] || "#ef4444";

          return (
            <Circle
              key={`density-circle-${selectedDensityFilter}-${seg.road_edge_id || idx}`}
              center={centerPos}
              radius={analysisRadiusMeters <= 500 ? 50 : 75}
              pathOptions={{
                color:       filterColor,
                fillColor:   filterColor,
                fillOpacity: 0.35,
                weight:      2,
              }}
            >
              <Popup opacity={0.98}>
                <div className="p-2 space-y-1.5 text-slate-800 font-sans text-xs min-w-[170px]">
                  <div className="font-extrabold uppercase tracking-wider text-[10px] text-slate-400 border-b pb-1">
                    ROAD TRAFFIC DENSITY
                  </div>
                  <div className="font-bold text-slate-900 text-sm">
                    {seg.road_name || seg.road_edge_id || "Road Segment"}
                  </div>
                  <div className="flex justify-between items-center text-xs pt-1">
                    <span className="text-slate-500">Density Level:</span>
                    <span className={`font-bold px-1.5 py-0.5 rounded text-white text-[10px] ${
                      selectedDensityFilter === "HIGH" ? "bg-red-600" : selectedDensityFilter === "MEDIUM" ? "bg-amber-500" : "bg-emerald-600"
                    }`}>
                      {selectedDensityFilter}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-500">Estimated Vehicles:</span>
                    <span className="font-bold text-slate-900">{seg.vehicle_count || seg.estimated_vehicles || 5}</span>
                  </div>
                </div>
              </Popup>
            </Circle>
          );
        })}

        {/* ── Small Blue Dots: Raw GPS User Observations ───────────────── */}
        {validObservations.map((obs, idx) => {
          if (!obs.latitude || !obs.longitude) return null;

          return (
            <CircleMarker
              key={`obs-${obs.observation_id || idx}`}
              center={[obs.latitude, obs.longitude]}
              radius={currentZoom >= 15 ? 3.5 : 2.5}
              pathOptions={{
                color:       "#ffffff",
                fillColor:   "#2563eb",
                fillOpacity: getObservationOpacity(),
                weight:      0.8,
              }}
            >
              <Tooltip direction="top" offset={[0, -3]} opacity={0.9}>
                <div className="text-[10px] font-sans">
                  <div className="font-bold text-blue-700">GPS User Observation</div>
                  <div>User ID: {obs.user_id}</div>
                  <div>Speed: {obs.speed_kmh} km/h</div>
                </div>
              </Tooltip>
            </CircleMarker>
          );
        })}

        {/* ── DBSCAN Vehicle Clusters (Translucent Boundary + Green Marker [Count]) ── */}
        {clusters.map((c, idx) => {
          if (!c.center_latitude || !c.center_longitude) return null;
          
          const rawIdStr = c.cluster_id ? c.cluster_id.toString().replace(/\D/g, '') : "";
          const parsedId = rawIdStr ? parseInt(rawIdStr, 10) : (idx + 1);
          const clusterNum = isNaN(parsedId) ? (idx + 1) : parsedId;
          const userCount = c.user_count || c.size || (c.user_ids ? c.user_ids.length : 4);
          
          const isSelected = selectedCluster?.cluster_id === c.cluster_id;
          const clusterRadiusMeters = Math.min(45, Math.max(20, userCount * 5));

          return (
            <div key={`cluster-group-${c.cluster_id || idx}`}>
              
              {/* Translucent Cluster Spatial Grouping Boundary */}
              <Circle
                center={[c.center_latitude, c.center_longitude]}
                radius={clusterRadiusMeters}
                pathOptions={{
                  color:       isSelected ? "#2563eb" : "#059669",
                  fillColor:   "#10b981",
                  fillOpacity: viewMode === "Clusters" ? 0.14 : 0.06,
                  weight:      isSelected ? 1.5 : 1,
                  dashArray:   "3, 3",
                }}
              />

              {/* Count Badge above cluster center dot */}
              <Marker
                position={[c.center_latitude + 0.0002, c.center_longitude]}
                icon={createClusterCountIcon(userCount, isSelected)}
                eventHandlers={{ click: () => setSelectedCluster(isSelected ? null : c) }}
              />

              {/* Cluster Center Marker Dot */}
              <CircleMarker
                center={[c.center_latitude, c.center_longitude]}
                radius={isSelected ? 9 : 6}
                pathOptions={{
                  color:       "#ffffff",
                  fillColor:   isSelected ? "#2563eb" : "#10b981",
                  fillOpacity: getClusterOpacity(),
                  weight:      2,
                }}
                eventHandlers={{ click: () => setSelectedCluster(isSelected ? null : c) }}
              >
                <Popup opacity={0.98} className="custom-cluster-popup">
                  <div className="p-3 min-w-[200px] space-y-2 text-slate-800 font-sans">
                    <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                      <span className="font-extrabold text-sm text-slate-900 uppercase">
                        CLUSTER #{clusterNum}
                      </span>
                      <span className="text-[10px] font-extrabold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                        1 Vehicle
                      </span>
                    </div>
                    
                    {/* Story explanation in popup */}
                    <div className="bg-blue-50 dark:bg-slate-800 p-2 rounded text-[11px] font-semibold text-blue-900 dark:text-blue-200">
                      {userCount} users grouped → 1 estimated vehicle
                    </div>

                    <div className="text-xs space-y-1.5 pt-1">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Average Speed:</span>
                        <span className="font-bold text-slate-900">{c.avg_speed_kmh || c.average_speed_kmh || 28.6} km/h</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Road:</span>
                        <span className="font-bold text-slate-800 truncate max-w-[110px]">{c.primary_road_edge_id || "Outer Ring Road"}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Cluster Purity:</span>
                        <span className="font-bold text-emerald-600">{c.cluster_purity || "100"}%</span>
                      </div>
                    </div>

                    <div className="text-[10px] text-slate-500 italic pt-2 border-t border-slate-100">
                      "These nearby user observations are treated as one vehicle."
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            </div>
          );
        })}

      </MapContainer>

      {/* ── MAP FILTER ACTIVE BADGE OVERLAY (Floating Top-Center) ───────── */}
      {selectedDensityFilter && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] bg-slate-900/90 backdrop-blur-md text-white border border-slate-700 rounded-full px-3.5 py-1.5 shadow-lg flex items-center gap-2 text-xs font-sans">
          <Filter className="w-3.5 h-3.5 text-indigo-400" />
          <span className="font-bold tracking-wider text-[11px]">
            MAP FILTER: <span className={`uppercase font-black ${
              selectedDensityFilter === "HIGH" ? "text-red-400" : selectedDensityFilter === "MEDIUM" ? "text-amber-400" : "text-emerald-400"
            }`}>{selectedDensityFilter} DENSITY</span>
          </span>
          <button
            onClick={clearDensityFilter}
            className="ml-1 text-slate-400 hover:text-white p-0.5 rounded-full hover:bg-slate-800 transition focus:outline-none cursor-pointer"
            title="Clear Filter"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* ── MAP LEGEND OVERLAY (Floating Top-Left) ───────────────────────── */}
      <div className="absolute top-4 left-4 z-[1000] bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border border-slate-200/90 dark:border-slate-800 rounded-lg p-2.5 shadow-md text-xs space-y-2 min-w-[185px] font-sans">
        <div className="font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider text-[10px] flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-1">
          <span>MAP LEGEND</span>
          {selectedDensityFilter && (
            <span className="text-[9px] font-extrabold text-indigo-600 dark:text-indigo-400">FILTERED</span>
          )}
        </div>
        
        <div className="space-y-1.5 text-[11px] font-semibold text-slate-700 dark:text-slate-300">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-600 inline-block shadow-xs shrink-0" />
            <span>User Observation</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block shadow-xs shrink-0" />
            <span>Cluster / Estimated Vehicle</span>
          </div>
          
          <div className="pt-1 border-t border-slate-100 dark:border-slate-800 space-y-1">
            {(!selectedDensityFilter || selectedDensityFilter === "HIGH") && (
              <div className="flex items-center gap-2">
                <span className="w-4 h-1 bg-red-500 inline-block rounded shrink-0" />
                <span>High Density Road</span>
              </div>
            )}
            {(!selectedDensityFilter || selectedDensityFilter === "MEDIUM") && (
              <div className="flex items-center gap-2">
                <span className="w-4 h-1 bg-amber-500 inline-block rounded shrink-0" />
                <span>Medium Density Road</span>
              </div>
            )}
            {(!selectedDensityFilter || selectedDensityFilter === "LOW") && (
              <div className="flex items-center gap-2">
                <span className="w-4 h-1 bg-emerald-500 inline-block rounded shrink-0" />
                <span>Low Density Road</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
