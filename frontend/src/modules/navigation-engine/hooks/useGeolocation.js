import { useState, useCallback } from "react";

export const useGeolocation = () => {
  const [coords, setCoords] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getCurrentLocation = useCallback((onSuccess, onError) => {
    if (!navigator.geolocation) {
      const err = "Geolocation is not supported by your browser";
      setError(err);
      if (onError) onError(err);
      return;
    }

    setLoading(true);
    setError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const userCoords = [position.coords.latitude, position.coords.longitude];
        setCoords(userCoords);
        setLoading(false);
        if (onSuccess) onSuccess(userCoords);
      },
      (err) => {
        setError(err.message);
        setLoading(false);
        if (onError) onError(err.message);
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  }, []);

  return { coords, loading, error, getCurrentLocation };
};
