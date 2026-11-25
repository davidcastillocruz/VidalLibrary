import { useCallback, useEffect, useState } from 'react';

import { api } from '@/utils/api';

// The params that say something: an empty filter isn't sent
function cleanParams(params) {
  return Object.fromEntries(Object.entries(params).filter(([, value]) => value !== '' && value !== null && value !== undefined));
}

// Loads what a page shows with GET url?params: on mount, whenever url or params change, and with reload(). Not when the
// language changes: what it loads isn't translated (names, titles, dates), and the pages write their own texts.
// A null url asks nothing. { data, error, loading, reload }: data stays
// while it reloads, so the page doesn't blink; error is the failed request (an axios error)
export function useRequest(url, params = {}) {
  const [version, setVersion] = useState(0);
  const key = url ? JSON.stringify([url, cleanParams(params), version]) : null;
  const [result, setResult] = useState({ key: null, data: undefined, error: null });

  useEffect(() => {
    if (!key) return undefined;
    const [path, query] = JSON.parse(key);
    let current = true;
    api.get(path, { params: query }).then(
      ({ data }) => current && setResult({ key, data, error: null }),
      (error) => current && setResult((previous) => ({ ...previous, key, error })),
    );
    // An answer that arrives after the page asked again (or left) is dropped
    return () => {
      current = false;
    };
  }, [key]);

  const reload = useCallback(() => setVersion((value) => value + 1), []);

  return { data: result.data, error: result.error, loading: Boolean(key) && result.key !== key, reload };
}
