export interface GpuPrice {
  provider: string;
  gpu_id: string;
  display_name: string | null;
  memory_gb: number | null;
  instance_type: string;
  price_per_hour: number;
  currency: string;
  stock_status: string | null;
  fetched_at: string;
  canonical_name: string;
  all_time_low: number;
  all_time_high: number;
  observation_count: number;
  first_seen_at: string;
}
