import { use } from 'react';

import { CurrentUserContext } from './CurrentUserContext';

// Who is signed in, refresh() after signing in and signOut(), in any component inside CurrentUserProvider
export function useCurrentUser() {
  const context = use(CurrentUserContext);
  if (!context) throw new Error('useCurrentUser must be used inside CurrentUserProvider');
  return context;
}
