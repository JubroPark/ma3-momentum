const BASE =
  'https://raw.githubusercontent.com/JubroPark/ma3-momentum/data';

export const URLS = {
  signals: `${BASE}/outputs/signals.json`,
  masam:   `${BASE}/outputs/masam.json`,
  market:  `${BASE}/outputs/market.json`,
} as const;
