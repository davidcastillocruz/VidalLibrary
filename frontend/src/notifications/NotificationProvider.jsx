import { useCallback, useRef, useState } from 'react';

import { useLanguage } from '@/languages/useLanguage';

import { NotificationContext } from './NotificationContext';
import Toasts from './Toasts';

// Toasts on screen at once; a new one pushes out the oldest
const MAX_TOASTS = 3;

// Toasts of the style guide: short confirmations at the bottom right that don't stop the user. Each one leaves by
// itself or with its close button. A text in another language than the page's is hidden but its time still runs:
// a backend text only exists in the language of its request
export default function NotificationProvider({ children }) {
  const { language } = useLanguage();
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const notify = useCallback(
    ({ tone = 'success', title, text, language: textLanguage }) => {
      nextId.current += 1;
      const toast = { id: nextId.current, tone, title, text, language: textLanguage ?? language };
      setToasts((current) => [...current, toast].slice(-MAX_TOASTS));
    },
    [language],
  );

  return (
    <NotificationContext value={notify}>
      {children}
      <Toasts toasts={toasts} language={language} onDismiss={dismiss} />
    </NotificationContext>
  );
}
