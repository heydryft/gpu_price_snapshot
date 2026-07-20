import { useState, useEffect } from 'react';
import { GpuCard } from './components/GpuCard';
import { ComparisonView } from './components/ComparisonView';
import { HistoryChart } from './components/HistoryChart';
import { getLatestPrices, getComparison, getGpuHistory } from './api/client';
import type { GpuPrice, GpuComparison } from './types';
import { RefreshCw, Activity } from 'lucide-react';

function App() {
  const [prices, setPrices] = useState<GpuPrice[]>([]);
  const [comparisons, setComparisons] = useState<GpuComparison[]>([]);
  const [selectedGpu, setSelectedGpu] = useState<{ id: string; name: string } | null>(null);
  const [gpuHistory, setGpuHistory] = useState<GpuPrice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<'dashboard' | 'comparison' | 'history'>('dashboard');
  const [providerFilter, setProviderFilter] = useState<'all' | 'runpod' | 'vast'>('all');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [pricesData, comparisonData] = await Promise.all([
        getLatestPrices(),
        getComparison(),
      ]);
      setPrices(pricesData);
      setComparisons(comparisonData.comparison);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const loadGpuHistory = async (gpuId: string, gpuName: string) => {
    try {
      const historyData = await getGpuHistory(gpuId);
      setGpuHistory(historyData.history);
      setSelectedGpu({ id: gpuId, name: gpuName });
      setView('history');
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  };

  // Group prices by GPU
  const providerCounts = {
    runpod: new Set(prices.filter(price => price.provider === 'runpod').map(price => price.canonical_name)).size,
    vast: new Set(prices.filter(price => price.provider === 'vast').map(price => price.canonical_name)).size,
  };
  const visiblePrices = providerFilter === 'all'
    ? prices
    : prices.filter(price => price.provider === providerFilter);
  const groupedPrices = visiblePrices.reduce((acc, price) => {
    const key = `${price.provider}-${price.canonical_name}`;
    if (!acc[key]) acc[key] = [];
    acc[key].push(price);
    return acc;
  }, {} as Record<string, GpuPrice[]>);

  const gpuList = Object.values(groupedPrices).sort((a, b) => {
    const providerOrder = a[0].provider.localeCompare(b[0].provider);
    return providerOrder || a[0].canonical_name.localeCompare(b[0].canonical_name);
  });

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <Activity className="w-8 h-8 text-purple-600" />
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                GPU Index
              </h1>
            </div>
            <div className="flex items-center gap-4">
              <nav className="flex gap-2">
                <button
                  onClick={() => setView('dashboard')}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    view === 'dashboard'
                      ? 'bg-purple-600 text-white'
                      : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  Dashboard
                </button>
                <button
                  onClick={() => setView('comparison')}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    view === 'comparison'
                      ? 'bg-purple-600 text-white'
                      : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  Compare
                </button>
              </nav>
              <button
                onClick={loadData}
                disabled={loading}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
                title="Refresh data"
              >
                <RefreshCw className={`w-5 h-5 text-gray-600 dark:text-gray-300 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error ? (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-2">Error Loading Data</h3>
            <p className="text-red-700 dark:text-red-300">{error}</p>
            <p className="text-sm text-red-600 dark:text-red-400 mt-2">Make sure the backend server is running on http://localhost:8000</p>
            <button
              onClick={loadData}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Retry
            </button>
          </div>
        ) : loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
          </div>
        ) : view === 'dashboard' ? (
          <>
            <div className="mb-7 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wider text-purple-600 dark:text-purple-400">Live marketplace index</p>
                <h2 className="mt-1 text-2xl font-bold text-slate-950 dark:text-white">Latest verified GPU prices</h2>
                <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                  Each provider uses its own latest successful fetch, so both marketplaces remain visible.
                </p>
              </div>
              <div className="inline-flex w-fit rounded-xl bg-slate-200/70 p-1 dark:bg-slate-800">
                {([
                  ['all', 'All', providerCounts.runpod + providerCounts.vast],
                  ['runpod', 'RunPod', providerCounts.runpod],
                  ['vast', 'Vast.ai', providerCounts.vast],
                ] as const).map(([value, label, count]) => (
                  <button
                    key={value}
                    onClick={() => setProviderFilter(value)}
                    className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${providerFilter === value ? 'bg-white text-slate-950 shadow-sm dark:bg-slate-700 dark:text-white' : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'}`}
                  >
                    {label} <span className="ml-1 opacity-60">{count}</span>
                  </button>
                ))}
              </div>
            </div>
            {gpuList.length > 0 ? (
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                {gpuList.map(gpuPrices => (
                  <div key={`${gpuPrices[0].provider}-${gpuPrices[0].canonical_name}`} onClick={() => loadGpuHistory(gpuPrices[0].gpu_id, gpuPrices[0].canonical_name)}>
                    <GpuCard prices={gpuPrices} />
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
                No verified {providerFilter === 'all' ? '' : providerFilter === 'runpod' ? 'RunPod' : 'Vast.ai'} GPU prices were found in the latest fetch.
              </div>
            )}
          </>
        ) : view === 'comparison' ? (
          <ComparisonView comparisons={comparisons} />
        ) : view === 'history' && selectedGpu ? (
          <div>
            <button
              onClick={() => setView('dashboard')}
              className="mb-4 text-purple-600 hover:text-purple-700 dark:text-purple-400 font-medium"
            >
              ← Back to Dashboard
            </button>
            <HistoryChart history={gpuHistory} gpuName={selectedGpu.name} />
          </div>
        ) : null}
      </main>

      {/* Footer */}
      <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-gray-600 dark:text-gray-400 text-sm">
            Data updated hourly • Prices in USD/hour
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
