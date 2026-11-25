import { Navigate, Outlet, useLocation } from 'react-router';

import { useCurrentUser } from '@/features/auth/currentUser/useCurrentUser';
import NotFoundPage from '@/pages/NotFoundPage/NotFoundPage';

// The pages behind it need a session: a guest goes to sign in, and comes back after it. With role="librarian", a
// reader finds nothing there, as if the page didn't exist. While the session is asked, nothing shows
export default function RequireRole({ role }) {
  const { user } = useCurrentUser();
  const location = useLocation();

  if (user === undefined) return null;
  if (user === null) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  if (role && user.role !== role) return <NotFoundPage />;
  return <Outlet />;
}
