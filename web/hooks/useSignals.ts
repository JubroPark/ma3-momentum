'use client';
import useSWR from 'swr';
import { URLS } from '@/lib/urls';
import type { SignalsJson } from '@/types/signals';

const fetcher = (url: string) => fetch(url).then(r => r.json());

export function useSignals() {
  const { data, error, isLoading } = useSWR<SignalsJson>(
    URLS.signals,
    fetcher,
    { refreshInterval: 60 * 60 * 1000, revalidateOnFocus: false, dedupingInterval: 0 }
  );
  return { data, error, isLoading };
}
