import { TrendingDown, TrendingUp, Minus, ExternalLink } from 'lucide-react';
import { formatINR } from '../services/api';
import type { ProductSearchResult } from '../types';

interface Props {
  product: ProductSearchResult;
  onViewHistory: (product: ProductSearchResult) => void;
  onAskAI: (product: ProductSearchResult) => void;
}

export default function ProductCard({ product, onViewHistory, onAskAI }: Props) {
  const discount = product.mrp && product.current_price
    ? Math.round(((product.mrp - product.current_price) / product.mrp) * 100)
    : null;

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow overflow-hidden">
      {product.image_url && (
        <div className="h-48 bg-gray-50 flex items-center justify-center p-4">
          <img src={product.image_url} alt={product.title} className="max-h-full object-contain" />
        </div>
      )}
      <div className="p-4 space-y-3">
        <div>
          <span className="text-xs font-medium text-blue-600 uppercase tracking-wide">
            {product.marketplace}
          </span>
          <h3 className="font-semibold text-gray-900 text-sm leading-snug mt-0.5 line-clamp-2">
            {product.title}
          </h3>
        </div>

        <div className="space-y-1">
          {product.current_price && (
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-gray-900">
                {formatINR(product.current_price)}
              </span>
              {discount && discount > 0 && (
                <span className="text-green-600 text-sm font-medium">
                  {discount}% off MRP
                </span>
              )}
            </div>
          )}
          {product.mrp && (
            <div className="text-sm text-gray-500 line-through">
              MRP {formatINR(product.mrp)}
            </div>
          )}
          {product.effective_price && product.effective_price !== product.current_price && (
            <div className="text-sm text-green-700 font-medium">
              Effective: {formatINR(product.effective_price)} (after coupon)
            </div>
          )}
        </div>

        {!product.availability && (
          <span className="inline-block text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
            Out of stock
          </span>
        )}

        <div className="flex gap-2 pt-1">
          <button
            onClick={() => onViewHistory(product)}
            className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium py-2 rounded-xl transition-colors"
          >
            Price History
          </button>
          <button
            onClick={() => onAskAI(product)}
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium py-2 rounded-xl transition-colors"
          >
            Ask AI
          </button>
        </div>

        {product.url && (
          <a
            href={product.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-blue-600 transition-colors"
          >
            <ExternalLink size={12} />
            View on {product.marketplace}
          </a>
        )}
      </div>
    </div>
  );
}
