import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { formatINR } from '../services/api';
import type { PriceAnalysis, PriceHistoryPoint } from '../types';

interface Props {
  history: PriceHistoryPoint[];
  analysis?: PriceAnalysis;
}

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr);
  return `${d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })}`;
};

export default function PriceHistoryChart({ history, analysis }: Props) {
  if (!history.length) {
    return (
      <div className="bg-gray-50 rounded-2xl p-8 text-center text-gray-500">
        No price history available yet.
      </div>
    );
  }

  // Thin out data for readability (max 90 points)
  const stride = Math.max(1, Math.floor(history.length / 90));
  const chartData = history.filter((_, i) => i % stride === 0).map((p) => ({
    date: formatDate(p.date),
    price: p.price,
    source: p.source,
  }));

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-900">Price History</h3>
        {analysis && (
          <span className="text-xs text-gray-500">
            {analysis.history_coverage_days} days · {analysis.observation_count} observations
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: '#9ca3af' }}
            interval={Math.floor(chartData.length / 6)}
          />
          <YAxis
            tick={{ fontSize: 11, fill: '#9ca3af' }}
            tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
            width={55}
          />
          <Tooltip
            formatter={(val: number) => [formatINR(val), 'Price']}
            labelStyle={{ color: '#374151' }}
          />
          <Legend />

          <Line
            type="monotone"
            dataKey="price"
            stroke="#2563eb"
            strokeWidth={2}
            dot={false}
            name="Selling Price"
          />

          {analysis?.historical_average && (
            <ReferenceLine
              y={analysis.historical_average}
              stroke="#f59e0b"
              strokeDasharray="4 4"
              label={{ value: `Avg ${formatINR(analysis.historical_average)}`, fill: '#f59e0b', fontSize: 11, position: 'right' }}
            />
          )}
          {analysis?.historical_minimum && (
            <ReferenceLine
              y={analysis.historical_minimum}
              stroke="#10b981"
              strokeDasharray="4 4"
              label={{ value: `Low ${formatINR(analysis.historical_minimum)}`, fill: '#10b981', fontSize: 11, position: 'right' }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>

      <p className="text-xs text-gray-400 mt-2">
        Source: {history[0]?.source || 'DealGuard collector'}
        {history[0]?.source === 'mock_historical' && ' — synthetic data for development'}
      </p>
    </div>
  );
}
