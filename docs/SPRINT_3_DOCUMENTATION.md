# RouteFlow - Sprint 3 Documentation
## Navigation Engine & Interactive Map Integration

### Map Engine Overview
Sprint 3 successfully transitions RouteFlow into a production-grade Navigation Platform. This sprint established a clean, modular **Navigation Engine** architecture (`src/modules/navigation-engine/`) and integrated an interactive OpenStreetMap canvas powered by Leaflet. The engine is robust, responsive, gracefully handles geolocation and tile loading errors using the RouteFlow Toast system, and scales efficiently for future route tracking features.

---

### Map Components

The Navigation Engine separates state and presentation through specialized React components:
- **NavigationWorkspace**: The main entry point container that provides the `NavigationEngineContext` to the entire map module.
- **MapContainer**: Initializes the `react-leaflet` instance, handles global tile loading errors via toasts, and houses the primary TileLayer.
- **ControlPanel**: A floating UI container housing map interaction tools.
  - **LocateMeButton**: Triggers geolocation, handles permissions, and manages error toasts.
  - **ResetViewButton**: Returns the map camera back to the default origin.
  - **ZoomControls**: Clean, theme-compliant custom zoom buttons.
- **CurrentLocationMarker**: A dedicated component for rendering the user's localized blue-dot pin without cluttering the layer manager.

---

### Layer Architecture
A scalable `LayerManager` registers vector-based layers that inject directly into the Map coordinates. In Sprint 3, these remain lightweight, optimized placeholders that currently return `null` and avoid dummy data overhead.
- **MarkerLayer**: Prepared structure for rendering dynamic destination markers.
- **RouteLayer**: Prepared structure for navigation path polylines.
- **TrafficLayer**: Prepared for live segment congestion rendering.
- **VehicleLayer**: Prepared for real-time fleet movement animations.
- **ClusterLayer**: Prepared for grouping dense marker sets using clustering algorithms.

---

### Overlay Architecture
A synchronized `OverlayManager` controls DOM overlays sitting above the map (z-index managed) to maintain a non-blocking interactive map canvas while displaying rich UI panels. Like the layers, these are clean placeholders ready for business logic integration.
- **SearchOverlay**: Floating navigation search panel slots.
- **RouteOverlay**: UI panels for route instruction steps.
- **VehicleOverlay**: Telemetry data overlays for selected fleet vehicles.
- **TrafficOverlay**: Global traffic legend and settings panel.
- **ClusterOverlay**: Breakout lists for clustered areas.

---

### Current Location Flow
1. **Trigger**: User clicks the `Locate Me` button.
2. **Permission Handling**: The browser prompts for geolocation access. 
3. **Success State**:
   - `useGeolocation` retrieves precise coordinates.
   - Updates `currentLocation` state in `NavigationContext`.
   - `useMapInstance` executes a smooth `flyTo` animation to the new coordinates at Zoom 15.
   - `CurrentLocationMarker` renders the animated blue dot.
4. **Error/Denial State**:
   - If the user denies permission, or the browser is unsupported, the error is caught.
   - The RouteFlow `Toast` notification system gracefully informs the user ("Location access denied") at the bottom-right.
   - The map remains safely at the default coordinates (Bangalore: 12.9716, 77.5946, Zoom 13).

---

### Developer Notes
- **Map Tile Configuration**: Tile URLs are controlled via `src/modules/navigation-engine/constants/engineConstants.js`.
- **Leaflet Marker Icons**: Leaflet standard marker icon URL overrides are configured in `MapContainer.jsx` to prevent broken image assets.
- **Error Handling**: Native `alert()` is strictly prohibited; all engine errors must use the unified `Toast` component.
