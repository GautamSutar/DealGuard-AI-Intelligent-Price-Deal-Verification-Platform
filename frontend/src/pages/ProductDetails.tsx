import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, MessageSquare, ExternalLink } from 'lucide-react';
import { getPriceAnalysis, getPriceHistory, formatINR } from '../services/api';
import type { PriceAnalysis, PriceHistoryPoint } from '../types';
import PriceHistoryChart from '../components/PriceHistoryChart';
import AnalysisSummary from '../components/AnalysisSummary';

export default function ProductDetails() {
  const { listingId } = useParams<{ listingId: string }>();
  const [history, setHistory] = useState<PriceHistoryPoint[]>([]);
  const [analysis, setAnalysis] = useState<PriceAnalysis | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!listingId) return;
    (async () => {
      try {
        const [h, a] = await Promise.all([
          getPriceHistory(listingId),
          getPriceAnalysis(listingId),
        ]);
        setHistory(h);
        setAnalysis(a);
      } finally {
        setLoading(false);
      }
    })();
  }, [listingId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-3" />
          <p className="text-gray-500">Loading price data…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <Link to="/" className="flex items-center gap-2 text-gray-500 hover:text-blue-600 mb-6 transition-colors">
          <ArrowLeft size={18} />
          Back to search
        </Link>

        {analysis && (
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-gray-900 mb-1">{analysis.title}</h1>
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <span className="capitalize">{analysis.marketplace}</span>
              <span>·</span>
              <span>{analysis.history_coverage_days} days of history</span>
              {analysis.current_effective_price && (
                <>
                  <span>·</span>
                  <span className="text-2xl font-bold text-gray-900">
                    {formatINR(analysis.current_effective_price)}
                  </span>
                </>
              )}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <PriceHistoryChart history={history} analysis={analysis ?? undefined} />
          </div>
          <div className="space-y-4">
            {analysis && <AnalysisSummary analysis={analysis} />}
            <Link
              to={`/chat?listing_id=${listingId}&title=${encodeURIComponent(analysis?.title ?? '')}`}
              className="flex items-center justify-center gap-2 w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-xl font-medium transition-colors"
            >
              <MessageSquare size={18} />
              Ask AI about this product
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
