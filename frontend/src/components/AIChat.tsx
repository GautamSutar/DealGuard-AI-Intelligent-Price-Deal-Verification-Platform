import { Send, Bot, User, Loader2 } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { sendChatMessage } from '../services/api';
import type { ChatMessage } from '../types';

interface Props {
  sessionId: string;
  productId?: string;
  initialQuery?: string;
}

const EXAMPLE_QUESTIONS = [
  'Is this a good time to buy?',
  'Was this product cheaper last month?',
  'Show me the lowest price ever recorded',
  'Is this discount actually significant?',
  'Compare current price with historical average',
];

export default function AIChat({ sessionId, productId, initialQuery }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (initialQuery && messages.length === 0) {
      handleSend(initialQuery);
    }
  }, [initialQuery]);

  const handleSend = async (text: string = input) => {
    if (!text.trim() || loading) return;

    const userMsg: ChatMessage = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await sendChatMessage(sessionId, text, productId);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.message,
          data: response.data,
          sources: response.sources,
          tool_calls_made: response.tool_calls_made,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I could not process your request. Please try again.' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-gray-100 bg-gradient-to-r from-blue-600 to-blue-700">
        <Bot size={20} className="text-white" />
        <div>
          <p className="font-semibold text-white text-sm">DealGuard AI</p>
          <p className="text-blue-200 text-xs">Powered by verified price data</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="space-y-3">
            <p className="text-center text-gray-500 text-sm py-4">
              Ask me anything about this product's pricing history
            </p>
            {EXAMPLE_QUESTIONS.map((q) => (
              <button
                key={q}
                onClick={() => handleSend(q)}
                className="w-full text-left text-sm bg-gray-50 hover:bg-blue-50 hover:text-blue-700 text-gray-600 px-4 py-2.5 rounded-xl border border-gray-200 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
              msg.role === 'user' ? 'bg-blue-600' : 'bg-gray-100'
            }`}>
              {msg.role === 'user'
                ? <User size={16} className="text-white" />
                : <Bot size={16} className="text-gray-600" />
              }
            </div>
            <div className={`max-w-[80%] space-y-2 ${msg.role === 'user' ? 'items-end' : 'items-start'} flex flex-col`}>
              <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white rounded-tr-sm'
                  : 'bg-gray-100 text-gray-800 rounded-tl-sm'
              }`}>
                {msg.content}
              </div>
              {msg.tool_calls_made && msg.tool_calls_made.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {msg.tool_calls_made.map((tool) => (
                    <span key={tool} className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full border border-blue-100">
                      {tool}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">
              <Bot size={16} className="text-gray-600" />
            </div>
            <div className="bg-gray-100 px-4 py-3 rounded-2xl rounded-tl-sm flex items-center gap-2">
              <Loader2 size={16} className="animate-spin text-gray-500" />
              <span className="text-sm text-gray-500">Analysing price data…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-gray-100">
        <form
          onSubmit={(e) => { e.preventDefault(); handleSend(); }}
          className="flex gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about price history, deals, trends…"
            className="flex-1 bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-blue-400 transition-colors"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white p-2.5 rounded-xl transition-colors"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
