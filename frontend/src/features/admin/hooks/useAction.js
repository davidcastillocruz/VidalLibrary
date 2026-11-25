import { useCallback, useState } from 'react';

import { requestError, useNoticeText } from '@/hooks/useSubmit';
import { useLanguage } from '@/languages/useLanguage';
import { useNotify } from '@/notifications/useNotify';

// Runs the changes of the management: running is the key of the one on its way (to show its spinner), and the answer
// of the backend comes as a toast. run(key, request, failedTitle) resolves to the data, or null when it failed
export function useAction() {
  const { language } = useLanguage();
  const notify = useNotify();
  const noticeText = useNoticeText();
  const [running, setRunning] = useState(null);

  const run = useCallback(
    async (key, request, failedTitle) => {
      setRunning(key);
      try {
        const { data } = await request();
        if (data?.message) notify({ tone: 'success', text: data.message, language });
        return data ?? {};
      } catch (error) {
        notify({ tone: 'error', title: failedTitle, text: noticeText(requestError(error, language)), language });
        return null;
      } finally {
        setRunning(null);
      }
    },
    [language, noticeText, notify],
  );

  return { run, running };
}
