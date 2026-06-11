const TICKER_COLORS: Record<string, string> = {
  AAPL: '#555555', MSFT: '#00a4ef', NVDA: '#76b900',
  AMZN: '#ff9900', TSLA: '#e82127', GOOGL: '#4285f4',
  META: '#0082fb', JPM: '#003087', 'BRK-B': '#5f4c3a',
  LLY: '#d52b1e', JNJ: '#cc0000', XOM: '#ce1126',
  CVX: '#0044a0', COST: '#e31837', WMT: '#0071ce',
  AVGO: '#cc092f',
};

export const tickerColor = (ticker: string): string =>
  TICKER_COLORS[ticker] ?? '#3182f6';

export const tickerInitials = (ticker: string): string =>
  ticker.replace('-', '').slice(0, 2).toUpperCase();

export const fmtPct = (v: number, digits = 1): string =>
  `${v >= 0 ? '+' : ''}${(v * 100).toFixed(digits)}%`;

export const fmtScore = (v: number): string =>
  `${Math.round(v)}점`;
