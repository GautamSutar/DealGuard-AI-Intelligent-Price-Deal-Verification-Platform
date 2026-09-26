import { AlertCircle, CheckCircle, TrendingDown, TrendingUp, Minus } from 'lucide-react';
import { formatINR, formatPct } from '../services/api';
import type { PriceAnalysis } from '../types';

interface Props {
  analysis: PriceAnalysis;
}

const CLASSIFICATION_LABELS: Record<string, { label: string; color: string; icon: JSX.Element }> = {
  NEAR_HISTORICAL_LOW: { label: 'Near Historical Low', color: 'text-green-700 bg-green-50 border-green-200', icon: <TrendingDown size={16} /> },
  BELOW_HISTORICAL_AVERAGE: { label: 'Below Average', color: 'text-green-600 bg-green-50 border-green-200', icon: <TrendingDown size={16} /> },
  AROUND_HISTORICAL_AVERAGE: { label: 'Around Average', color: 'text-yellow-700 bg-yellow-50 border-yellow-200', icon: <Minus size={16} /> },
  ABOVE_HISTORICAL_AVERAGE: { label: 'Above Average', color: 'text-red-600 bg-red-50 border-red-200', icon: <TrendingUp size={16} /> },
  NEW_DATA_INSUFFICIENT: { label: 'Insufficient Data', color: 'text-gray-600 bg-gray-50 border-gray-200', icon: <AlertCircle size={16} /> },
  PRICE_INCREASING: { label: 'Price Rising', color: 'text-red-600 bg-red-50 border-red-200', icon: <TrendingUp size={16} /> },
  PRICE_DECREASING: { label: 'Price Falling', color: 'text-green-600 bg-green-50 border-green-200', icon: <TrendingDown size={16} /> },
  PRICE_VOLATILE: { label: 'Volatile Pricing', color: 'text-orange-600 bg-orange-50 border-orange-200', icon: <AlertCircle size={16} /> },
};

function StatRow({ label, value, highlight }: { label: string; value?: string; highlight?: boolean }) {
  return (
    <div className={`flex justify-between items-center py-2.5 border-b border-gray-100 last:border-0 ${highlight ? 'font-semibold' : ''}`}>
      <span className="text-gray-600 text-sm">{label}</span>
      <span className={`text-sm ${highlight ? 'text-gray-900' : 'text-gray-700'}`}>{value ?? '—'}</span>
    </div>
  );
}

export default function AnalysisSummary({ analysis }: Props) {
  const cls = analysis.classification ? CLASSIFICATION_LABELS[analysis.classification] : null;

  return (
    <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
      <div className="p-5 border-b border-gray-100">
        <h3 className="font-semibold text-gray-900 mb-3">Price Analysis</h3>
        {cls && (
          <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-medium ${cls.color}`}>
            {cls.icon}
            {cls.label}
          </div>
        )}
      </div>

      <div className="p-5 space-y-0">
        <StatRow label="Current Effective Price" value={analysis.current_effective_price ? formatINR(analysis.current_effective_price) : undefined} highlight />
        <StatRow label="Historical Average" value={analysis.historical_average ? formatINR(analysis.historical_average) : undefined} />
        <StatRow label="Historical Median" value={analysis.historical_median ? formatINR(analysis.historical_median) : undefined} />
        <StatRow label="Historical Low" value={analysis.historical_minimum ? formatINR(analysis.historical_minimum) : undefined} />
        <StatRow label="Historical High" value={analysis.historical_maximum ? formatINR(analysis.historical_maximum) : undefined} />
        <StatRow
          label="vs Historical Average"
          value={analysis.pct_vs_average !== undefined && analysis.pct_vs_average !== null ? formatPct(analysis.pct_vs_average) : undefined}
        />
        <StatRow
          label="vs Historical Low"
          value={analysis.pct_vs_minimum !== undefined && analysis.pct_vs_minimum !== null ? formatPct(analysis.pct_vs_minimum) : undefined}
        />
        <StatRow label="7-day Average" value={analysis.avg_7d ? formatINR(analysis.avg_7d) : undefined} />
        <StatRow label="30-day Average" value={analysis.avg_30d ? formatINR(analysis.avg_30d) : undefined} />
        <StatRow label="Price Trend" value={analysis.price_trend ?? undefined} />
        <StatRow label="History Coverage" value={`${analysis.history_coverage_days} days`} />
        <StatRow label="Observations" value={`${analysis.observation_count}`} />
      </div>

      {analysis.classification_reasons.length > 0 && (
        <div className="px-5 pb-5">
          <p className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">Evidence</p>
          <ul className="space-y-1">
            {analysis.classification_reasons.map((reason, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                <CheckCircle size={14} className="text-blue-500 mt-0.5 shrink-0" />
                {reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="px-5 pb-5 pt-2 bg-blue-50 border-t border-blue-100">
        <p className="text-xs text-blue-700 font-medium">
          The final purchasing decision is yours. This analysis shows evidence — not a recommendation to buy.
        </p>
      </div>
    </div>
  );
}
