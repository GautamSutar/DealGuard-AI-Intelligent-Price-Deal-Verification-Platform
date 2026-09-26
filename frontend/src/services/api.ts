import axios from 'axios';
import type { ChatResponse, PriceAnalysis, PriceHistoryPoint, ProductSearchResult } from '../types';

const API = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

export const searchProducts = async (
  query: string,
  marketplace?: string
): Promise<ProductSearchResult[]> => {
  const { data } = await API.post('/search', { query, marketplace });
  return data;
};

export const getPriceHistory = async (
  listingId: string,
  days = 365
): Promise<PriceHistoryPoint[]> => {
  const { data } = await API.get(`/products/${listingId}/history`, { params: { days } });
  return data;
};

export const getPriceAnalysis = async (listingId: string): Promise<PriceAnalysis> => {
  const { data } = await API.get(`/products/${listingId}/analysis`);
  return data;
};

export const sendChatMessage = async (
  sessionId: string,
  message: string,
  productId?: string
): Promise<ChatResponse> => {
  const { data } = await API.post('/chat', {
    session_id: sessionId,
    message,
    product_id: productId,
  });
  return data;
};

export const formatINR = (amount: number): string =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);

export const formatPct = (pct: number): string => {
  const sign = pct > 0 ? '+' : '';
  return `${sign}${pct.toFixed(1)}%`;
};
