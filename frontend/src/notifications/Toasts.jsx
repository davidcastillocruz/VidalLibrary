import { useEffect, useRef, useState } from 'react';

import Icon from '@/components/Icon/Icon';
import { useT } from '@/languages/useT';

import styles from './ToastsStyle.module.css';
import translations from './ToastsTranslation.json';

// How long a toast stays; errors stay longer to be read
const DURATION_MS = { success: 4500, info: 4500, error: 8000 };

// Length of the fade-out in the CSS; the toast is removed after it
const LEAVE_MS = 160;

// Icon of each tone, so the tone isn't told by color alone
const ICONS = { success: 'check', error: 'alert', info: 'info' };

// One toast. The pointer over it or the focus inside it pauses its time, each one separately.
// hidden: its text is in another language than the page's. region: where the focus goes if the toast closes with it
// inside, instead of falling to the start of the page
function Toast({ toast, hidden, region, onDismiss }) {
  const t = useT(translations);
  const [leaving, setLeaving] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const paused = hovered || focused;
  const left = useRef(DURATION_MS[toast.tone]);
  const item = useRef(null);

  useEffect(() => {
    if (leaving) {
      const timer = setTimeout(() => {
        if (item.current.contains(document.activeElement)) region.current.focus();
        onDismiss(toast.id);
      }, LEAVE_MS);
      return () => clearTimeout(timer);
    }
    if (paused) return undefined;
    const started = Date.now();
    const timer = setTimeout(() => setLeaving(true), left.current);
    return () => {
      clearTimeout(timer);
      left.current -= Date.now() - started;
    };
  }, [leaving, paused, onDismiss, region, toast.id]);

  return (
    <li
      ref={item}
      className={`${styles.toast} ${styles[toast.tone]}`}
      data-leaving={leaving || undefined}
      hidden={hidden}
      onPointerEnter={() => setHovered(true)}
      onPointerLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
    >
      <span className={styles.icon}>
        <Icon name={ICONS[toast.tone]} size={14} />
      </span>
      <div className={styles.body}>
        {toast.title && <p className={styles.title}>{toast.title}</p>}
        <p className={styles.text}>{toast.text}</p>
      </div>
      <button type="button" className={styles.close} aria-label={t('close')} onClick={() => setLeaving(true)}>
        <Icon name="close" size={14} />
      </button>
    </li>
  );
}

// The stack of toasts, newest at the bottom. The region is always there and is the live one, so screen readers read
// each toast as it arrives, politely: a toast never interrupts. language: the page's
export default function Toasts({ toasts, language, onDismiss }) {
  const t = useT(translations);
  const region = useRef(null);

  return (
    <section ref={region} className={styles.region} aria-label={t('region')} aria-live="polite" tabIndex={-1}>
      <ol className={styles.list}>
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            toast={toast}
            hidden={toast.language !== language}
            region={region}
            onDismiss={onDismiss}
          />
        ))}
      </ol>
    </section>
  );
}
