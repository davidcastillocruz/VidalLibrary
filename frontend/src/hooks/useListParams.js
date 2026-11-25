import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router';

// How long the search waits after the last key before asking, in ms: one request per word, not per letter
export const SEARCH_DELAY = 300;

// Longest search of a list, in characters: SEARCH_MAX_LENGTH of the schemas of the backend
export const SEARCH_MAX_LENGTH = 100;

// The filters of a list kept in the address (?kind=film&q=pa&page=2), so a search can be shared and the back button
// works. change(values) sets some of them and goes back to the first page; an empty value leaves the address.
// search is the text of the search box: it reaches ?q= once the user stops typing, and follows ?q= when it changes
// from outside (a link, the back button)
export function useListParams() {
  const [params, setParams] = useSearchParams();
  // The address and its setter as they are now: a search that waited SEARCH_DELAY keeps what changed meanwhile
  const latest = useRef({ params, setParams });
  useEffect(() => {
    latest.current = { params, setParams };
  }, [params, setParams]);

  const change = useCallback((values) => {
    const next = new URLSearchParams(latest.current.params);
    for (const [key, value] of Object.entries({ page: '', ...values })) {
      if (value) next.set(key, String(value));
      else next.delete(key);
    }
    latest.current = { ...latest.current, params: next };
    latest.current.setParams(next);
  }, []);

  const q = params.get('q') ?? '';
  const [search, setSearch] = useState(q);
  // The ?q= the box follows: a new one from outside replaces what the box says, unless it already says it
  const [followed, setFollowed] = useState(q);
  if (q !== followed) {
    setFollowed(q);
    if (search.trim() !== q) setSearch(q);
  }

  useEffect(() => {
    if (search.trim() === q) return undefined;
    const timer = setTimeout(() => change({ q: search.trim() }), SEARCH_DELAY);
    return () => clearTimeout(timer);
  }, [search, q, change]);

  return { params, change, search, setSearch };
}


// A page past the last one goes back to the last page with rows: the list shrank (its last row handed over or
// deleted), or the address is old. total: of the list loaded, undefined while it loads
export function useLastPage(page, total, pageSize, change) {
  useEffect(() => {
    if (total === undefined) return;
    const last = Math.max(1, Math.ceil(total / pageSize));
    if (page > last) change({ page: last === 1 ? '' : last });
  }, [page, total, pageSize, change]);
}
