import { useState } from 'react';
import { Shield, TrendingDown } from 'lucide-react';
import SearchBar from '../components/SearchBar';
import ProductCard from '../components/ProductCard';
import { searchProducts } from '../services/api';
import type { ProductSearchResult } from '../types';
import { useNavigate } from 'react-router-dom';

export default function Home() {
  const [results, setResults] = useState<ProductSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const navigate = useNavigate();

  const handleSearch = async (query: string) => {
    setLoading(true);
    setSearched(true);
    try {
      const data = await searchProducts(query);
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
      {/* Hero */}
      <div className="pt-16 pb-12 px-4">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="bg-blue-600 p-2.5 rounded-xl">
              <Shield size={28} className="text-white" />
            </div>
            <h1 className="text-4xl font-bold text-gray-900">DealGuard</h1>
          </div>
          <p className="text-lg text-gray-600 leading-relaxed">
            Is that Amazon discount actually good?<br />
            <span className="text-blue-600 font-medium">Compare current prices against real historical data.</span>
          </p>
          <p className="text-sm text-gray-400 mt-2">
            Not a store. No ads. No affiliate pressure. Just price intelligence.
          </p>
        </div>

        <SearchBar onSearch={handleSearch} loading={loading} />
      </div>

      {/* Results */}
      <div className="max-w-6xl mx-auto px-4 pb-16">
        {loading && (
          <div className="text-center py-16 text-gray-500">
            <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-3" />
            Searching for products…
          </div>
        )}

        {searched && !loading && results.length === 0 && (
          <div className="text-center py-16 text-gray-500">
            No products found. Try a different search query.
          </div>
        )}

        {results.length > 0 && (
          <>
            <p className="text-sm text-gray-500 mb-4">{results.length} result{results.length > 1 ? 's' : ''} found</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {results.map((product) => (
                <ProductCard
                  key={product.listing_id}
                  product={product}
                  onViewHistory={(p) => navigate(`/product/${p.listing_id}`)}
                  onAskAI={(p) => navigate(`/chat?listing_id=${p.listing_id}&title=${encodeURIComponent(p.title)}`)}
                />
              ))}
            </div>
          </>
        )}

        {!searched && (
          <div className="mt-12 grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-3xl mx-auto">
            {[
              { icon: '📊', title: 'Historical Price Data', desc: 'See how the price has moved over months and years.' },
              { icon: '🤖', title: 'AI-Powered Analysis', desc: 'Ask questions in plain language. Get evidence-backed answers.' },
              { icon: '🔍', title: 'Transparent Evidence', desc: 'Every claim is backed by real data. No hidden motives.' },
            ].map((f) => (
              <div key={f.title} className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm text-center">
                <div className="text-3xl mb-3">{f.icon}</div>
                <h3 className="font-semibold text-gray-900 mb-1">{f.title}</h3>
                <p className="text-sm text-gray-500">{f.desc}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
