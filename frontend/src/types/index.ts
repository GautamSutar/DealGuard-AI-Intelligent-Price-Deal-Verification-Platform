export interface ProductSearchResult {
  listing_id: string;
  product_id: string;
  marketplace: string;
  title: string;
  brand?: string;
  image_url?: string;
  external_product_id: string;
  url?: string;
  current_price?: number;
  mrp?: number;
  effective_price?: number;
  currency: string;
  availability: boolean;
  last_checked_at?: string;
}

export interface PriceHistoryPoint {
  date: string;
  price: number;
  source: string;
}

export interface PriceAnalysis {
  listing_id: string;
  marketplace: string;
  title: string;
  current_price?: number;
  current_effective_price?: number;
  currency: string;
  historical_average?: number;
  historical_median?: number;
  historical_minimum?: number;
  historical_maximum?: number;
  avg_7d?: number;
  avg_30d?: number;
  avg_90d?: number;
  pct_vs_average?: number;
  pct_vs_median?: number;
  pct_vs_minimum?: number;
  pct_vs_maximum?: number;
  price_position?: number;
  price_trend?: string;
  observation_count: number;
  history_coverage_days: number;
  days_since_historical_low?: number;
  classification?: string;
  classification_reasons: string[];
  calculated_at?: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  data?: Record<string, unknown>;
  sources?: ChatSource[];
  tool_calls_made?: string[];
}

export interface ChatSource {
  type: string;
  marketplace?: string;
  description: string;
}

export interface ChatResponse {
  session_id: string;
  message: string;
  data?: Record<string, unknown>;
  sources: ChatSource[];
  tool_calls_made: string[];
}

export interface Offer {
  id: string;
  offer_type: string;
  title?: string;
  description?: string;
  discount_value?: number;
  discount_percentage?: number;
  coupon_code?: string;
  eligibility?: string;
  is_conditional: boolean;
}
