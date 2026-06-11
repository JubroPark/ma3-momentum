'use client';
import useSWR from 'swr';
import { URLS } from '@/lib/urls';
import { fetcher } from '@/lib/fetcher';
import type { MasamJson } from '@/types/signals';

export function useMasam() {
  const { data, error, isLoading } = useSWR<MasamJson>(
    URLS.masam,
    fetcher,
    { refreshInterval: 60 * 60 * 1000, revalidateOnFocus: false, shouldRetryOnError: false, errorRetryCount: 0 }
  );
  return { data, error, isLoading };
}
