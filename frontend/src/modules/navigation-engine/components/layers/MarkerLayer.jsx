import { SourceMarker } from "./SourceMarker";
import { DestinationMarker } from "./DestinationMarker";
import { MapFlyEffect } from "./MapFlyEffect";
import { RoadNodeDebugMarkers } from "./RoadNodeDebugMarkers";

/**
 * MarkerLayer — Sprint 5.4
 *
 * Renders source and destination location markers, camera fly effects,
 * and optional dev-only road node debug markers.
 */
export const MarkerLayer = () => {
  return (
    <>
      <SourceMarker />
      <DestinationMarker />
      <MapFlyEffect />
      <RoadNodeDebugMarkers />
    </>
  );
};
