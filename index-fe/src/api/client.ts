import type { GpuPrice } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

export async function fetchPrices(): Promise<GpuPrice[]> {
  const response = await fetch(`${API_BASE}/api/gpus/latest`);
  if (!response.ok) {
    throw new Error(`API request failed (${response.status})`);
  }
  const data = await response.json();
  return data.prices as GpuPrice[];
}
