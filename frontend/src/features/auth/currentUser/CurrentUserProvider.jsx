import { useCallback, useEffect, useMemo, useState } from 'react';

import { api } from '@/utils/api';

import { CurrentUserContext } from './CurrentUserContext';

// GET /user/me: the user, or null for a guest (a 401, or no answer)
const askWho = () => api.get('/user/me').then(({ data }) => data, () => null);

// Who is signed in, asked once for the whole app: the user, null for a guest, undefined while asking. refresh() asks
// again after signing in; signOut() resolves to { closed, message }, or { closed: false, error }
export default function CurrentUserProvider({ children }) {
  const [user, setUser] = useState(undefined);

  useEffect(() => {
    askWho().then(setUser);
  }, []);

  const refresh = useCallback(
    () =>
      askWho().then((found) => {
        setUser(found);
        return found;
      }),
    [],
  );

  const signOut = useCallback(async () => {
    try {
      const { data } = await api.post('/auth/logout');
      setUser(null);
      return { closed: true, message: data.message };
    } catch (error) {
      // A 401 means the session had already expired, so it's closed too. Any other error keeps it on screen
      if (error.response?.status !== 401) return { closed: false, error };
      setUser(null);
      return { closed: true, message: null };
    }
  }, []);

  const value = useMemo(() => ({ user, refresh, signOut }), [user, refresh, signOut]);

  return <CurrentUserContext value={value}>{children}</CurrentUserContext>;
}
