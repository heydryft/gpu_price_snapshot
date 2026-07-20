import type { GpuPrice } from '../types';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

interface HistoryChartProps {
  history: GpuPrice[];
  gpuName: string;
}

export function HistoryChart({ history, gpuName }: HistoryChartProps) {
  const chartData = history.map(p => ({
    time: new Date(p.fetched_at).toLocaleDateString([], { month: 'short', day: 'numeric' }),
    fullTime: new Date(p.fetched_at).toLocaleString(),
    price: p.price_per_hour,
    instanceType: p.instance_type,
  }));

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        {gpuName} - Price History
      </h3>
      
      {chartData.length > 0 ? (
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
              <XAxis 
                dataKey="time" 
                stroke="#6b7280"
                tick={{ fill: '#6b7280' }}
              />
              <YAxis 
                stroke="#6b7280"
                tick={{ fill: '#6b7280' }}
                tickFormatter={(value) => `$${value.toFixed(2)}`}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'rgba(0, 0, 0, 0.8)',
                  border: 'none',
                  borderRadius: '4px',
                  color: 'white'
                }}
                labelFormatter={(label) => chartData.find(d => d.time === label)?.fullTime || label}
                formatter={(value) => `$${Number(value).toFixed(3)}/hr`}
              />
              <Line 
                type="monotone" 
                dataKey="price" 
                stroke="#8b5cf6" 
                strokeWidth={2}
                dot={{ fill: '#8b5cf6', r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="text-gray-500 dark:text-gray-400">No history data available</p>
      )}
    </div>
  );
}
