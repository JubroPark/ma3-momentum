'use client';
import useSWR from 'swr';
import { URLS } from '@/lib/urls';
import type { MasamJson } from '@/types/signals';

const fetcher = (url: string) => fetch(url).then(r => r.json());

export function useMasam() {
  const { data, error, isLoading } = useSWR<MasamJson>(
    URLS.masam,
    fetcher,
    { refreshInterval: 60 * 60 * 1000, revalidateOnFocus: false }
  );
  return { data, error, isLoading };
}
