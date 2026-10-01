import { useState, useEffect, useCallback } from 'react';
import { apiClient, HealthCheckResponse } from '../services/api.ts';

export interface UseBackendHealthResult {
  isHealthy: boolean;
  isConnecting: boolean;
  health: HealthCheckResponse | null;
  error: string | null;
  lastChecked: string | null;
  refresh: () => Promise<void>;
}

export function useBackendHealth(pollIntervalMs = 25000): UseBackendHealthResult {
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);
  const [isConnecting, setIsConnecting] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<string | null>(null);

  const check = useCallback(async () => {
    try {
      const data = await apiClient.checkHealth();
      setHealth(data);
      setError(null);
      setLastChecked(new Date().toLocaleTimeString());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Backend unreachable';
      setError(msg);
      setHealth(null);
      setLastChecked(new Date().toLocaleTimeString());
    } finally {
      setIsConnecting(false);
    }
  }, []);

  useEffect(() => {
    check();
    const timer = setInterval(check, pollIntervalMs);
    return () => clearInterval(timer);
  }, [check, pollIntervalMs]);

  return {
    isHealthy: health?.status === 'ok',
    isConnecting,
    health,
    error,
    lastChecked,
    refresh: check,
  };
}
