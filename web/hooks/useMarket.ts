'use client';
import useSWR from 'swr';
import { URLS } from '@/lib/urls';
import { fetcher } from '@/lib/fetcher';
import type { MarketJson } from '@/types/market';

export function useMarket() {
  const { data, error, isLoading } = useSWR<MarketJson>(
    URLS.market,
    fetcher,
    { refreshInterval: 60 * 60 * 1000, revalidateOnFocus: false, shouldRetryOnError: false, errorRetryCount: 0 }
  );
  return { data, error, isLoading };
}
