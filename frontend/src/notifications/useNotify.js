import { use } from 'react';

import { NotificationContext } from './NotificationContext';

// notify({ tone, title, text, language }) in any component inside NotificationProvider:
//   tone: success, error or info. title: optional. text: what happened, already in the language of the page.
//   language: the one of a text of the backend (the language of its request); without it, the current one
export function useNotify() {
  const notify = use(NotificationContext);
  if (!notify) throw new Error('useNotify must be used inside NotificationProvider');
  return notify;
}
