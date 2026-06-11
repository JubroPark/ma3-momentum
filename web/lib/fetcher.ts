export const fetcher = (url: string) =>
  fetch(url).then(r => {
    if (!r.ok) throw new Error(`Fetch failed: ${r.status} ${r.url}`);
    return r.json();
  });
