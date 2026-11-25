import { useCallback, useEffect, useRef } from 'react';

// For an action whose button can disappear when its list reloads (a cancelled reservation moves to the history, a
// loan handed over gets other buttons): once the new data arrives, the focus goes to target if it was left on <body>.
// target goes on what announces the result (tabIndex={-1}); call expect() when the action ends, before reloading
export function useFocusAfterReload(data) {
  const target = useRef(null);
  const pending = useRef(false);

  useEffect(() => {
    if (pending.current && document.activeElement === document.body) target.current?.focus();
    pending.current = false;
  }, [data]);

  const expect = useCallback(() => {
    pending.current = true;
  }, []);

  return { target, expect };
}
