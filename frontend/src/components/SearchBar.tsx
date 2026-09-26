import { Search } from 'lucide-react';
import { useState } from 'react';

interface Props {
  onSearch: (query: string) => void;
  loading?: boolean;
}

const SUGGESTION_CHIPS = [
  'iPhone 16 128GB',
  'Samsung 55 inch 4K TV',
  'Sony WH-1000XM5',
  'Gaming laptop under 70000',
];

export default function SearchBar({ onSearch, loading }: Props) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) onSearch(query.trim());
  };

  return (
    <div className="w-full max-w-3xl mx-auto">
      <form onSubmit={handleSubmit} className="relative">
        <div className="flex items-center gap-3 bg-white border-2 border-gray-200 rounded-2xl px-4 py-3 shadow-lg focus-within:border-blue-500 transition-colors">
          <Search className="text-gray-400 shrink-0" size={22} />
          <input
            className="flex-1 text-lg outline-none placeholder-gray-400"
            placeholder="Search a product or paste an Amazon/Flipkart URL..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-5 py-2 rounded-xl font-semibold transition-colors"
          >
            {loading ? 'Searching…' : 'Search'}
          </button>
        </div>
      </form>

      <div className="flex flex-wrap gap-2 mt-4 justify-center">
        {SUGGESTION_CHIPS.map((chip) => (
          <button
            key={chip}
            onClick={() => { setQuery(chip); onSearch(chip); }}
            className="bg-gray-100 hover:bg-blue-50 hover:text-blue-700 text-gray-600 text-sm px-4 py-1.5 rounded-full border border-gray-200 transition-colors"
          >
            {chip}
          </button>
        ))}
      </div>
    </div>
  );
}
