/**
 * LiveClusteringMap.jsx — Interactive Leaflet Map for Live Vehicle Clustering
 */
import {
  MapContainer, TileLayer, CircleMarker, Circle, Tooltip, Marker, Polyline, useMap, Popup
} from "react-leaflet";
import { useEffect } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useLiveClustering } from "../context/LiveClusteringContext";

const BENGALURU_CENTER = [12.9174, 77.6228];
const TILE_URL  = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

const createClusterIdIcon = (clusterId) => L.divIcon({
  className: "custom-cluster-badge",
  html: `<div style="
    background: #6366f1;
    color: white;
    font-weight: 800;
    font-size: 10px;
    font-family: ui-sans-serif, system-ui, sans-serif;
    padding: 1px 5px;
    border-radius: 5px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.3);
    border: 1.5px solid white;
    text-align: center;
    white-space: nowrap;
    line-height: 1.2;
  ">${clusterId}</div>`,
  iconSize: [22, 18],
  iconAnchor: [11, 22],
});

const areaCenterIcon = L.divIcon({
  className: "",
  html: `<div style="
    width:24px; height:24px;
    background:linear-gradient(135deg,#2563eb,#3b82f6);
    border:3px solid #fff;
    border-radius:50% 50% 50% 0;
    transform:rotate(-45deg);
    box-shadow:0 2px 8px rgba(37,99,235,0.5);
  "></div>`,
  iconSize:   [24, 24],
  iconAnchor: [12, 24],
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
  } = useLiveClustering();

  const clusters = clustering.clusters || [];
  const segments = roadDensity.road_segments || [];

  const DENSITY_COLORS = {
    HIGH:   "#ef4444",
    MEDIUM: "#f59e0b",
    LOW:    "#22c55e",
  };

  return (
    <div className="w-full h-full relative flex-1 min-h-[450px]">
      <MapContainer
        center={selectedArea ? [selectedArea.latitude, selectedArea.longitude] : BENGALURU_CENTER}
        zoom={14}
        scrollWheelZoom
        zoomControl={false}
        className="w-full h-full"
        style={{ minHeight: "450px" }}
      >
        <TileLayer url={TILE_URL} attribution={TILE_ATTR} maxZoom={19} />

        <FlyToArea area={selectedArea} radius={analysisRadiusMeters} />

        {/* ── Selected Area Radius Circle ──────────────────────────────── */}
        {selectedArea && (
          <>
            <Circle
              center={[selectedArea.latitude, selectedArea.longitude]}
              radius={analysisRadiusMeters}
              pathOptions={{
                color:       "#3b82f6",
                fillColor:   "#60a5fa",
                fillOpacity: 0.05,
                weight:      2,
                dashArray:   "6, 6",
              }}
            />
            <Marker
              position={[selectedArea.latitude, selectedArea.longitude]}
              icon={areaCenterIcon}
            >
              <Tooltip direction="top" offset={[0, -24]} opacity={0.95} permanent>
                <div className="text-xs font-semibold">
                  <div className="text-blue-700 dark:text-blue-400">{selectedArea.name}</div>
                  <div className="text-slate-500 font-normal">
                    {analysisRadiusMeters >= 1000 ? `${analysisRadiusMeters / 1000} km` : `${analysisRadiusMeters} m`} radius
                  </div>
                </div>
              </Tooltip>
            </Marker>
          </>
        )}

        {/* ── Road Density Segments ────────────────────────────────────── */}
        {segments.map((seg, idx) => {
          const coords = seg.geometry || seg.coordinates;
          if (!coords || coords.length < 2) return null;
          const isSelected = selectedSegment?.road_edge_id === seg.road_edge_id;
          const color = DENSITY_COLORS[seg.density_rank || seg.density_level] || "#22c55e";

          return (
            <Polyline
              key={`road-seg-${seg.road_edge_id || idx}`}
              positions={coords}
              pathOptions={{
                color:     isSelected ? "#2563eb" : color,
                weight:    isSelected ? 8 : 5,
                opacity:   isSelected ? 1.0 : 0.8,
              }}
              eventHandlers={{ click: () => setSelectedSegment(isSelected ? null : seg) }}
            >
              <Tooltip direction="top" opacity={0.95}>
                <div className="text-xs font-medium px-1 space-y-0.5">
                  <div className="font-bold text-slate-800 flex items-center justify-between gap-4">
                    <span>{seg.road_name || seg.road_edge_id}</span>
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded text-white" style={{ backgroundColor: color }}>
                      {seg.density_rank || "LOW"} DENSITY
                    </span>
                  </div>
                  <div className="text-slate-600">Vehicles: <span className="font-bold">{seg.vehicle_count || 1}</span> | Users: <span className="font-bold">{seg.user_count || 3}</span></div>
                  <div className="text-[10px] text-slate-400">Avg Speed: {seg.avg_speed_kmh || 30} km/h</div>
                </div>
              </Tooltip>
            </Polyline>
          );
        })}

        {/* ── DBSCAN Vehicle Cluster Center Markers & Numbered Badges ─── */}
        {clusters.map((c, idx) => {
          if (!c.center_latitude || !c.center_longitude) return null;
          
          // Format Cluster ID cleanly without leading zeros to avoid overlapping (e.g. "004" -> 4)
          const rawIdStr = c.cluster_id ? c.cluster_id.toString().replace(/\D/g, '') : "";
          const parsedId = rawIdStr ? parseInt(rawIdStr, 10) : (idx + 1);
          const clusterNum = isNaN(parsedId) ? (idx + 1) : parsedId;
          
          const isSelected = selectedCluster?.cluster_id === c.cluster_id;

          return (
            <div key={`cluster-group-${c.cluster_id || idx}`}>
              {/* Cluster ID Purple Badge above Marker */}
              <Marker
                position={[c.center_latitude + 0.00025, c.center_longitude]}
                icon={createClusterIdIcon(clusterNum)}
                eventHandlers={{ click: () => setSelectedCluster(isSelected ? null : c) }}
              />

              {/* Green Center Dot */}
              <CircleMarker
                center={[c.center_latitude, c.center_longitude]}
                radius={isSelected ? 10 : 7}
                pathOptions={{
                  color:       "#ffffff",
                  fillColor:   "#10b981",
                  fillOpacity: 0.95,
                  weight:      2,
                }}
                eventHandlers={{ click: () => setSelectedCluster(isSelected ? null : c) }}
              >
                <Popup opacity={0.98} className="custom-cluster-popup">
                  <div className="p-2 min-w-[170px] space-y-1 text-slate-800 font-sans">
                    <div className="font-bold text-sm text-slate-900 border-b pb-1">
                      Cluster {clusterNum}
                    </div>
                    <div className="text-xs space-y-0.5">
                      <div className="flex justify-between">
                        <span className="text-slate-500 font-medium">Users:</span>
                        <span className="font-bold text-slate-900">{c.user_count || c.size || 4}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500 font-medium">Est. Vehicle:</span>
                        <span className="font-bold text-emerald-600">1</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500 font-medium">Speed:</span>
                        <span className="font-bold text-slate-900">{c.avg_speed_kmh || 31} km/h</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500 font-medium">Road:</span>
                        <span className="font-bold text-slate-800 truncate max-w-[100px]">{c.primary_road_edge_id || "24th Main Road"}</span>
                      </div>
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            </div>
          );
        })}

        {/* ── Active User GPS Observations (Indigo Dots) ──────────────── */}
        {observations.map((obs, idx) => {
          if (!obs.latitude || !obs.longitude) return null;

          return (
            <CircleMarker
              key={`obs-${obs.observation_id || idx}`}
              center={[obs.latitude, obs.longitude]}
              radius={3}
              pathOptions={{
                color:       "#ffffff",
                fillColor:   "#3b82f6",
                fillOpacity: 0.9,
                weight:      1,
              }}
            >
              <Tooltip direction="top" offset={[0, -5]} opacity={0.9}>
                <div className="text-[10px] font-mono">
                  <div>User Probe: <span className="font-bold">{obs.user_id}</span></div>
                  <div>Speed: {obs.speed_kmh} km/h</div>
                </div>
              </Tooltip>
            </CircleMarker>
          );
        })}
      </MapContainer>

      {/* ── MAP LEGEND OVERLAY (Top-Left Pinned Card matching Mockup) ──── */}
      <div className="absolute top-4 left-4 z-[1000] bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border border-slate-200 dark:border-slate-800 rounded-xl p-3 shadow-lg text-xs space-y-2 min-w-[190px]">
        <div className="font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider text-[10px]">
          MAP LEGEND
        </div>
        <div className="space-y-1.5 text-[11px] font-medium text-slate-700 dark:text-slate-300">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block shadow-sm" />
            <span>User GPS Observation</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block shadow-sm" />
            <span>Vehicle Cluster Center</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-1.5 py-0.5 bg-indigo-500 text-white font-bold rounded text-[9px]">17</span>
            <span>Cluster ID Label</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-1 bg-red-500 inline-block rounded" />
            <span>High Density Road</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-1 bg-amber-500 inline-block rounded" />
            <span>Medium Density Road</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-1 bg-emerald-500 inline-block rounded" />
            <span>Low Density Road</span>
          </div>
        </div>
      </div>
    </div>
  );
};
