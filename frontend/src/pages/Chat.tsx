import { useSearchParams, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useMemo } from 'react';
import AIChat from '../components/AIChat';

function generateSessionId() {
  return `session_${Date.now()}_${Math.random().toString(36).slice(2)}`;
}

export default function ChatPage() {
  const [searchParams] = useSearchParams();
  const listingId = searchParams.get('listing_id') ?? undefined;
  const title = searchParams.get('title') ?? 'this product';
  const sessionId = useMemo(() => generateSessionId(), []);
  const initialQuery = listingId ? `Analyse the price of ${title} and tell me if the current deal is good.` : undefined;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <div className="max-w-3xl mx-auto w-full px-4 py-6 flex flex-col" style={{ height: '100vh' }}>
        <Link to={listingId ? `/product/${listingId}` : '/'} className="flex items-center gap-2 text-gray-500 hover:text-blue-600 mb-4 transition-colors">
          <ArrowLeft size={18} />
          {listingId ? 'Back to product' : 'Back to search'}
        </Link>

        <div className="flex-1 min-h-0">
          <AIChat
            sessionId={sessionId}
            productId={listingId}
            initialQuery={initialQuery}
          />
        </div>
      </div>
    </div>
  );
}
