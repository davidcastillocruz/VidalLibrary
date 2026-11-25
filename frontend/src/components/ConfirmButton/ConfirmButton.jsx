import { useEffect, useRef, useState } from 'react';

import Button from '@/components/Button/Button';
import { useT } from '@/languages/useT';

import styles from './ConfirmButtonStyle.module.css';
import translations from './ConfirmButtonTranslation.json';

// How long the confirmation waits before going back to the first button, in ms
const CONFIRM_TIME = 5000;

// A button for what can't be undone: the first press asks, inside the page, and only the second one does it.
// It goes back by itself if nobody confirms. The focus follows: to "yes" when it asks, and back to the first button
// when it returns, unless it had already left (a confirmation that ran out while the user was somewhere else)
export default function ConfirmButton({ children, question, onConfirm, loading = false, variant = 'secondary' }) {
  const t = useT(translations);
  const [asking, setAsking] = useState(false);
  const root = useRef(null);
  const first = useRef(null);
  const yes = useRef(null);
  const asked = useRef(false);

  useEffect(() => {
    if (!asking) return undefined;
    const timer = setTimeout(() => setAsking(false), CONFIRM_TIME);
    return () => clearTimeout(timer);
  }, [asking]);

  // The button that was focused has just been replaced: the focus is on <body> unless the user moved it elsewhere
  useEffect(() => {
    const lost = document.activeElement === document.body || root.current?.contains(document.activeElement);
    if (asking) yes.current?.focus();
    else if (asked.current && lost) first.current?.focus();
    asked.current = asking;
  }, [asking]);

  return (
    <span ref={root} className={styles.root}>
      {!asking && !loading ? (
        <Button ref={first} variant={variant} onClick={() => setAsking(true)}>
          {children}
        </Button>
      ) : (
        <span className={styles.ask} role="group" aria-label={question}>
          <span className={styles.question}>{question}</span>
          <Button
            ref={yes}
            variant="danger"
            loading={loading}
            onClick={async () => {
              await onConfirm();
              setAsking(false);
            }}
          >
            {t('yes')}
          </Button>
          {!loading && (
            <Button variant="ghost" onClick={() => setAsking(false)}>
              {t('no')}
            </Button>
          )}
        </span>
      )}
    </span>
  );
}
