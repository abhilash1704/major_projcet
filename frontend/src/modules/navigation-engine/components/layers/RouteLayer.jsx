/**
 * RouteLayer — Sprint 11C
 *
 * Renders the active route with dynamic traffic severity colors:
 *  - LOW: Blue (#3b82f6)
 *  - MEDIUM: Orange (#f97316)
 *  - HIGH: Red (#ef4444)
 *
 * Highlights specific congested route segments in bold red/orange.
 * Renders up to 3 candidate alternative routes in distinct colors (Green, Cyan, Purple).
 * Highlights selected preview candidate routes during comparison.
 */
import { useEffect } from "react";
import { Polyline, CircleMarker, Tooltip, useMap } from "react-leaflet";
import { useNavigationEngineContext } from "../../context/NavigationEngineContext";

const SOURCE_MARKER = { radius: 9, color: "#16a34a", fillColor: "#22c55e", fillOpacity: 0.9, weight: 2 };
const DEST_MARKER   = { radius: 9, color: "#b91c1c", fillColor: "#ef4444", fillOpacity: 0.9, weight: 2 };

export const RouteLayer = () => {
  const { activeRoute, comparisonData, rerouteRecommendation, previewRoute, alternativeRoutes } = useNavigationEngineContext();
  const map = useMap();

  // Auto-fit bounds when active route changes
  useEffect(() => {
    if (!activeRoute || !activeRoute.nodes || activeRoute.nodes.length < 2) return;
    const coords = activeRoute.nodes
      .filter((n) => n.lat != null && n.lon != null)
      .map((n) => [n.lat, n.lon]);
    if (coords.length >= 2) {
      try {
        map.fitBounds(coords, { padding: [40, 40], maxZoom: 14 });
      } catch (_) {
        // map not ready yet — no-op
      }
    }
  }, [activeRoute, map]);

  if (!activeRoute || !activeRoute.nodes || activeRoute.nodes.length < 2) {
    return null;
  }

  const positions = activeRoute.nodes
    .filter((n) => n.lat != null && n.lon != null)
    .map((n) => [n.lat, n.lon]);

  if (positions.length < 2) return null;

  const srcPos  = positions[0];
  const dstPos  = positions[positions.length - 1];
  const distKm  = activeRoute.total_distance_km ?? 0;
  const etaSec  = activeRoute.total_travel_time_seconds ?? 0;
  const etaMins = Math.round(etaSec / 60);

  // Dynamic Route Traffic Styling
  const trafficLevel = rerouteRecommendation?.current_route?.traffic_level || activeRoute.traffic_level || "LOW";
  let activeColor = "#3b82f6"; // LOW blue
  let activeWeight = 6;
  let activeOpacity = 0.85;
  let activeDash = undefined;

  if (trafficLevel === "HIGH") {
    activeColor = "#ef4444"; // Red
    activeWeight = 7;
    activeOpacity = 0.95;
    activeDash = "10, 5"; // Visual pulsing effect
  } else if (trafficLevel === "MEDIUM") {
    activeColor = "#f97316"; // Orange
    activeWeight = 6;
    activeOpacity = 0.9;
  }

  const activeRouteStyle = {
    color: activeColor,
    weight: activeWeight,
    opacity: activeOpacity,
    dashArray: activeDash,
    lineJoin: "round",
    lineCap: "round",
  };

  // Congested route segment extraction
  const congestedSegments = rerouteRecommendation?.current_route?.congested_segments || [];

  // Extract candidate alternative routes for map rendering.
  // Priority: on-demand alternativeRoutes (from AlternativeRoutesCard) → rerouteRecommendation → comparisonData
  let candidateRoutes = [];
  if (alternativeRoutes && alternativeRoutes.length > 0) {
    candidateRoutes = alternativeRoutes;
  } else if (rerouteRecommendation?.alternatives && rerouteRecommendation.alternatives.length > 0) {
    candidateRoutes = rerouteRecommendation.alternatives;
  } else if (rerouteRecommendation?.alternative_routes && rerouteRecommendation.alternative_routes.length > 0) {
    candidateRoutes = rerouteRecommendation.alternative_routes;
  } else if (rerouteRecommendation?.alternative_route) {
    candidateRoutes = [rerouteRecommendation.alternative_route];
  } else if (comparisonData?.comparison) {
    const { astar, dijkstra } = comparisonData.comparison;
    const activeAlgo = activeRoute?.algorithm;
    let altRoute = null;
    if (activeAlgo === 'astar' && dijkstra?.success) altRoute = dijkstra;
    else if (activeAlgo === 'dijkstra' && astar?.success) altRoute = astar;
    if (altRoute) candidateRoutes = [{ ...altRoute, color: "#a855f7", label: "Comparison Alt" }];
  }


  // Extract preview route coordinates if selected
  let previewPositions = null;
  if (previewRoute && previewRoute.nodes) {
    previewPositions = previewRoute.nodes
      .filter((n) => n.lat != null && n.lon != null)
      .map((n) => [n.lat, n.lon]);
  }

  return (
    <>
      {/* 1. Candidate Alternative Route Polylines */}
      {candidateRoutes.map((cand, idx) => {
        if (!cand.nodes || cand.nodes.length < 2) return null;
        const candPositions = cand.nodes
          .filter((n) => n.lat != null && n.lon != null)
          .map((n) => [n.lat, n.lon]);

        if (candPositions.length < 2) return null;

        const isPreviewingThis = previewRoute && previewRoute.id === cand.id;
        const candColor = cand.color || (idx === 0 ? "#22c55e" : "#3b82f6");

        const candStyle = isPreviewingThis ? {
          color: candColor,
          weight: 8,
          opacity: 0.95,
          dashArray: "12, 6",
          lineJoin: "round",
          lineCap: "round",
        } : {
          color: candColor,
          weight: 5,
          opacity: previewRoute ? 0.35 : 0.85,
          dashArray: "8, 6",
          lineJoin: "round",
          lineCap: "round",
        };

        return (
          <Polyline key={cand.id || `cand_${idx}`} positions={candPositions} pathOptions={candStyle}>
            <Tooltip sticky>
              ⚡ {cand.label || `Alternative ${idx + 1}`}: {(cand.distance_km || cand.total_distance_km || 0).toFixed(1)} km · ~{Math.round((cand.travel_time_seconds || cand.total_duration_seconds || 0) / 60)} min
              {cand.improvement_percent ? ` (${cand.improvement_percent}% faster)` : ""}
            </Tooltip>
          </Polyline>
        );

      })}

      {/* 2. Main Active Route Polyline */}
      <Polyline positions={positions} pathOptions={activeRouteStyle}>
        <Tooltip sticky>
          🗺 Route ({trafficLevel} Traffic): {distKm.toFixed(1)} km · ~{etaMins} min
        </Tooltip>
      </Polyline>

      {/* 3. Congested Route Segment Highlight Overlays */}
      {congestedSegments.map((seg, idx) => {
        if (!seg.coords || seg.coords.length < 2) return null;
        const segColor = seg.traffic_level === "HIGH" ? "#dc2626" : "#ea580c";
        return (
          <Polyline
            key={`cong_seg_${idx}`}
            positions={seg.coords}
            pathOptions={{
              color: segColor,
              weight: 9,
              opacity: 0.95,
              lineJoin: "round",
              lineCap: "round"
            }}
          >
            <Tooltip sticky>
              ⚠️ Congested Segment: {seg.traffic_level} Traffic
            </Tooltip>
          </Polyline>
        );
      })}

      {/* 4. Start & Destination Markers */}
      <CircleMarker center={srcPos} pathOptions={SOURCE_MARKER}>
        <Tooltip direction="top" permanent={false}>
          📍 Start
        </Tooltip>
      </CircleMarker>

      <CircleMarker center={dstPos} pathOptions={DEST_MARKER}>
        <Tooltip direction="top" permanent={false}>
          🏁 Destination
        </Tooltip>
      </CircleMarker>
    </>
  );
};
