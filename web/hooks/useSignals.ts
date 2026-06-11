'use client';
import useSWR from 'swr';
import { URLS } from '@/lib/urls';
import { fetcher } from '@/lib/fetcher';
import type { SignalsJson } from '@/types/signals';

export function useSignals() {
  const { data, error, isLoading } = useSWR<SignalsJson>(
    URLS.signals,
    fetcher,
    { refreshInterval: 60 * 60 * 1000, revalidateOnFocus: false, shouldRetryOnError: false, errorRetryCount: 0 }
  );
  return { data, error, isLoading };
}
