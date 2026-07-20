import type { GpuPrice } from '../types';
import { cn } from '../lib/utils';

interface GpuCardProps {
  prices: GpuPrice[];
}

export function GpuCard({ prices }: GpuCardProps) {
  if (!prices.length) return null;

  const gpu = prices[0];
  const displayName = gpu.canonical_name || gpu.display_name || gpu.gpu_id;
  const memory = gpu.memory_gb ? `${Math.round(gpu.memory_gb)}GB` : 'N/A';
  
  // Group by instance type
  const byInstanceType = prices.reduce((acc, p) => {
    if (!acc[p.instance_type]) acc[p.instance_type] = [];
    acc[p.instance_type].push(p);
    return acc;
  }, {} as Record<string, GpuPrice[]>);

  // Get lowest price
  const lowestPrice = Math.min(...prices.map(p => p.price_per_hour));
  const highestPrice = Math.max(...prices.map(p => p.price_per_hour));

  // Chart data - use recent prices if available
  const priceOptions = Object.entries(byInstanceType)
    .map(([type, typePrices]) => ({
      type,
      price: Math.min(...typePrices.map(p => p.price_per_hour)),
    }))
    .sort((a, b) => a.price - b.price);

  const providerColors = {
    runpod: 'bg-blue-500',
    vast: 'bg-purple-500',
  };

  return (
    <div className="h-full cursor-pointer rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-md dark:border-slate-700 dark:bg-slate-800">
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className="font-semibold text-gray-900 dark:text-white text-lg">{displayName}</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">{memory} VRAM</p>
        </div>
        <span className={cn(
          'px-2 py-1 rounded text-xs font-medium text-white',
          providerColors[gpu.provider as keyof typeof providerColors] || 'bg-gray-500'
        )}>
          {gpu.provider}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Lowest</p>
          <p className="text-xl font-bold text-green-600 dark:text-green-400">
            ${lowestPrice.toFixed(3)}/hr
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Highest</p>
          <p className="text-xl font-bold text-gray-900 dark:text-white">
            ${highestPrice.toFixed(3)}/hr
          </p>
        </div>
      </div>

      {priceOptions.length > 0 && (
        <div className="mt-4 space-y-3 border-t border-slate-100 pt-4 dark:border-slate-700">
          {priceOptions.map(({ type, price }) => (
            <div key={type}>
              <div className="mb-1.5 flex items-center justify-between text-xs">
                <span className="capitalize text-slate-500 dark:text-slate-400">{type.replaceAll('_', ' ')}</span>
                <span className="font-semibold text-slate-800 dark:text-slate-100">${price.toFixed(3)}/hr</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700">
                <div
                  className={cn('h-full rounded-full', gpu.provider === 'runpod' ? 'bg-blue-500' : 'bg-violet-500')}
                  style={{ width: `${Math.max(8, (price / highestPrice) * 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="mt-4 text-xs text-slate-400">
        Updated {new Date(gpu.fetched_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
      </p>
    </div>
  );
}
