import type { GpuComparison, GpuHistory, GpuPrice } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`API request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function getLatestPrices(): Promise<GpuPrice[]> {
  const data = await getJson<{ prices: GpuPrice[] }>('/api/gpus/latest');
  return data.prices;
}

export function getGpuHistory(gpuId: string, hours: number = 168): Promise<GpuHistory> {
  return getJson(`/api/gpus/history/${encodeURIComponent(gpuId)}?hours=${hours}`);
}

export function getComparison(): Promise<{ comparison: GpuComparison[] }> {
  return getJson('/api/gpus/compare');
}
