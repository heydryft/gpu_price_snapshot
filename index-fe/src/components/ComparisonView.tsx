import { useState } from 'react';
import type { GpuComparison, PriceMetric } from '../types';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LabelList } from 'recharts';

interface ComparisonViewProps {
  comparisons: GpuComparison[];
}

export function ComparisonView({ comparisons }: ComparisonViewProps) {
  const [mode, setMode] = useState<'on_demand' | 'interruptible'>('on_demand');
  const [selectedName, setSelectedName] = useState('');

  // Filter to GPUs that have data from both providers
  const dualProviderGpus = comparisons.filter(gpu => gpu.runpod.length > 0 && gpu.vast.length > 0);
  const availableGpus = dualProviderGpus.filter(gpu => gpu[mode] !== null);
  const selectedGpu = availableGpus.find(gpu => gpu.canonical_name === selectedName) ?? availableGpus[0];
  const selectedMetric = selectedGpu?.[mode] ?? null;

  // Prepare chart data
  const chartData = selectedMetric ? [
    { provider: 'RunPod', price: selectedMetric.runpod_price, fill: '#2563eb' },
    { provider: 'Vast.ai', price: selectedMetric.vast_price, fill: '#7c3aed' },
  ] : [];

  const formatPrice = (price: number) => `$${price.toFixed(3)}`;
  const providerLabel = (provider: PriceMetric['cheaper_provider']) => provider === 'runpod' ? 'RunPod' : 'Vast.ai';

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800 sm:p-7">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wider text-violet-600 dark:text-violet-400">Provider comparison</p>
            <h2 className="mt-1 text-2xl font-bold text-slate-950 dark:text-white">RunPod vs Vast.ai</h2>
            <p className="mt-2 max-w-2xl text-sm text-slate-500 dark:text-slate-400">
              Like-for-like prices for normalized GPU models. On-demand excludes spot and bid pricing.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <div className="inline-flex rounded-xl bg-slate-100 p-1 dark:bg-slate-900">
              {(['on_demand', 'interruptible'] as const).map(option => (
                <button
                  key={option}
                  onClick={() => setMode(option)}
                  className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${mode === option ? 'bg-white text-slate-950 shadow-sm dark:bg-slate-700 dark:text-white' : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'}`}
                >
                  {option === 'on_demand' ? 'On-demand' : 'Spot / bid'}
                </button>
              ))}
            </div>
            <select
              value={selectedGpu?.canonical_name ?? ''}
              onChange={(event) => setSelectedName(event.target.value)}
              className="min-w-56 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 outline-none focus:border-violet-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
            >
              {availableGpus.map(gpu => (
                <option key={gpu.canonical_name} value={gpu.canonical_name}>{gpu.canonical_name}</option>
              ))}
            </select>
          </div>
        </div>

        {selectedGpu && selectedMetric ? (
          <div className="mt-8 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
            <div className="rounded-2xl bg-slate-50 p-4 dark:bg-slate-900/70 sm:p-6">
              <div className="mb-5 flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Selected GPU</p>
                  <h3 className="text-xl font-bold text-slate-950 dark:text-white">{selectedGpu.canonical_name}</h3>
                </div>
                <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                  {providerLabel(selectedMetric.cheaper_provider)} cheaper
                </span>
              </div>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 28, right: 16, left: 0, bottom: 0 }}>
                    <XAxis dataKey="provider" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 13, fontWeight: 600 }} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }} tickFormatter={(value) => `$${Number(value).toFixed(2)}`} width={54} />
                    <Tooltip cursor={{ fill: 'rgba(148, 163, 184, 0.1)' }} formatter={(value) => [`$${Number(value).toFixed(4)}/hr`, 'Price']} />
                    <Bar dataKey="price" radius={[10, 10, 2, 2]} maxBarSize={110}>
                      {chartData.map(item => <Cell key={item.provider} fill={item.fill} />)}
                      <LabelList dataKey="price" position="top" formatter={(value) => `$${Number(value).toFixed(3)}`} fill="#64748b" fontSize={13} fontWeight={700} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1">
              <MetricCard label="RunPod" value={`${formatPrice(selectedMetric.runpod_price)}/hr`} accent="blue" />
              <MetricCard label="Vast.ai" value={`${formatPrice(selectedMetric.vast_price)}/hr`} accent="violet" />
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5 dark:border-emerald-900 dark:bg-emerald-950/40">
                <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">Price discrepancy</p>
                <p className="mt-1 text-2xl font-black text-emerald-950 dark:text-emerald-100">{selectedMetric.difference_percent.toFixed(1)}%</p>
                <p className="mt-1 text-sm text-emerald-700 dark:text-emerald-300">Save {formatPrice(selectedMetric.difference_per_hour)}/hr with {providerLabel(selectedMetric.cheaper_provider)}</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-8 rounded-xl bg-slate-50 p-8 text-center text-slate-500 dark:bg-slate-900 dark:text-slate-400">
            No matched GPUs have {mode === 'on_demand' ? 'on-demand' : 'spot / bid'} prices from both providers.
          </div>
        )}
      </section>

      {availableGpus.length > 0 && (
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800">
          <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-700">
            <h3 className="font-bold text-slate-950 dark:text-white">All matched GPUs</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400">Sorted by largest percentage discrepancy</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500 dark:bg-slate-900 dark:text-slate-400">
                <tr><th className="px-5 py-3">GPU</th><th className="px-5 py-3">RunPod</th><th className="px-5 py-3">Vast.ai</th><th className="px-5 py-3">Difference</th><th className="px-5 py-3">Best value</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                {[...availableGpus].sort((a, b) => (b[mode]?.difference_percent ?? 0) - (a[mode]?.difference_percent ?? 0)).map(gpu => {
                  const metric = gpu[mode] as PriceMetric;
                  return (
                    <tr key={gpu.canonical_name} onClick={() => setSelectedName(gpu.canonical_name)} className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/50">
                      <td className="px-5 py-4 font-bold text-slate-900 dark:text-white">{gpu.canonical_name}</td>
                      <td className="px-5 py-4 text-blue-600 dark:text-blue-400">{formatPrice(metric.runpod_price)}/hr</td>
                      <td className="px-5 py-4 text-violet-600 dark:text-violet-400">{formatPrice(metric.vast_price)}/hr</td>
                      <td className="px-5 py-4 font-semibold text-slate-700 dark:text-slate-200">{metric.difference_percent.toFixed(1)}%</td>
                      <td className="px-5 py-4"><span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-bold text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">{providerLabel(metric.cheaper_provider)}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

function MetricCard({ label, value, accent }: { label: string; value: string; accent: 'blue' | 'violet' }) {
  const colors = accent === 'blue'
    ? 'border-blue-200 bg-blue-50 text-blue-950 dark:border-blue-900 dark:bg-blue-950/40 dark:text-blue-100'
    : 'border-violet-200 bg-violet-50 text-violet-950 dark:border-violet-900 dark:bg-violet-950/40 dark:text-violet-100';
  return (
    <div className={`rounded-2xl border p-5 ${colors}`}>
      <p className="text-sm font-medium opacity-70">{label}</p>
      <p className="mt-1 text-2xl font-black">{value}</p>
    </div>
  );
}
