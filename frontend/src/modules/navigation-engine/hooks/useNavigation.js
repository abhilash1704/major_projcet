import { useNavigationEngineContext } from "../context/NavigationEngineContext";

export const useNavigation = () => {
  const {
    currentLocation,
    setCurrentLocation,
    sourceLocation,
    setSourceLocation,
    destinationLocation,
    setDestinationLocation,
    activeRoute,
    setActiveRoute,
    trafficMode,
    setTrafficMode,
  } = useNavigationEngineContext();

  return {
    currentLocation,
    setCurrentLocation,
    sourceLocation,
    setSourceLocation,
    destinationLocation,
    setDestinationLocation,
    activeRoute,
    setActiveRoute,
    trafficMode,
    setTrafficMode,
  };
};
