import { useCallback } from 'react';

import { requestError, useNoticeText } from '@/hooks/useSubmit';
import { useLanguage } from '@/languages/useLanguage';
import { useT } from '@/languages/useT';
import { useNotify } from '@/notifications/useNotify';

import { useCurrentUser } from './useCurrentUser';
import translations from './useSignOutTranslation.json';

// Signs out and reports it in a toast: the backend's message, ours if the session had already expired, or why it
// couldn't be closed. Resolves to whether it closed
export function useSignOut() {
  const t = useT(translations);
  const { language } = useLanguage();
  const { signOut } = useCurrentUser();
  const notify = useNotify();
  const noticeText = useNoticeText();

  return useCallback(async () => {
    const { closed, message, error } = await signOut();
    if (!closed) {
      // A backend reason in another language (the language changed meanwhile) gives way to our generic one
      const text = noticeText(requestError(error, language)) || noticeText({ key: 'unexpected' });
      notify({ tone: 'error', title: t('failedTitle'), text, language });
    } else if (message) notify({ tone: 'success', text: message, language });
    else notify({ tone: 'success', text: t('closed') });
    return closed;
  }, [language, noticeText, notify, signOut, t]);
}
