import { useCallback, useState } from 'react';

import { useLanguage } from '@/languages/useLanguage';
import { useT } from '@/languages/useT';

import translations from './useSubmitTranslation.json';

// Minimum time the button's spinner turns: one full turn (.spinner in ButtonStyle), so a fast answer doesn't flash
export const MIN_SENDING_MS = 600;

// Resolves after ms
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// What to tell the user about a failed request: { status, text, language } with the backend's translated detail, or
// { status, key } with one of ours (unexpected: no detail; noConnection: no answer). Used by forms and useSignOut
export function requestError(error, language) {
  const status = error.response?.status ?? null;
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return { status, text: detail, language };
  return { status, key: error.response ? 'unexpected' : 'noConnection' };
}

// Text of a requestError notice in the current language. A backend text only shows in the language of its request
export function useNoticeText() {
  const t = useT(translations);
  const { language } = useLanguage();

  return useCallback(
    (notice) => {
      if (notice.key) return t(notice.key);
      return notice.language === language ? notice.text : '';
    },
    [language, t],
  );
}

// Sends a form's request and keeps its state: sending, and the error as { status, message }.
// submit(request) resolves to { data } or { error } (a requestError notice)
export function useSubmit() {
  const { language } = useLanguage();
  const noticeText = useNoticeText();
  const [sending, setSending] = useState(false);
  const [failure, setFailure] = useState(null);

  const submit = useCallback(
    async (request) => {
      setSending(true);
      setFailure(null);
      // Waits for the answer and for at least one full turn of the spinner
      const [answer] = await Promise.allSettled([request(), wait(MIN_SENDING_MS)]);
      setSending(false);
      if (answer.status === 'fulfilled') return { data: answer.value.data };

      // The backend translated its error into the language of the request
      const found = requestError(answer.reason, language);
      setFailure(found);
      return { error: found };
    },
    [language],
  );

  const error = failure && { status: failure.status, message: noticeText(failure) };

  return { submit, sending, error };
}
