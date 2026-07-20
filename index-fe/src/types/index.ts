export interface GpuPrice {
  provider: string;
  gpu_id: string;
  display_name: string | null;
  memory_gb: number | null;
  instance_type: string;
  price_per_hour: number;
  stock_status: string | null;
  fetched_at: string;
  canonical_name: string;
}

export interface PriceMetric {
  runpod_price: number;
  vast_price: number;
  difference_per_hour: number;
  difference_percent: number;
  cheaper_provider: 'runpod' | 'vast';
}

export interface GpuComparison {
  canonical_name: string;
  display_name: string;
  memory_gb: number | null;
  runpod: GpuPrice[];
  vast: GpuPrice[];
  on_demand: PriceMetric | null;
  interruptible: PriceMetric | null;
}

export interface GpuHistory {
  gpu_id: string;
  history: GpuPrice[];
}
