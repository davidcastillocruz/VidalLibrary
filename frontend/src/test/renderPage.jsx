import { render } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { vi } from 'vitest';

import { CurrentUserContext } from '@/features/auth/currentUser/CurrentUserContext';
import LanguageProvider from '@/languages/LanguageProvider';
import NotificationProvider from '@/notifications/NotificationProvider';
import ThemeProvider from '@/themes/ThemeProvider';

export const READER = { id: 'u-reader', email: 'pau@vidal.cat', name: 'Pau Vidal', role: 'reader' };
export const LIBRARIAN = { id: 'u-librarian', email: 'ana@vidal.cat', name: 'Ana Puig', role: 'librarian' };

// Renders routes at path, in Catalan and the light theme of the system, with a signed-in user (null: a guest) and the toasts. Returns the router (to
// read where it went) and the current-user functions, spied
export function renderPage(routes, { path = '/', user = null } = {}) {
  vi.spyOn(navigator, 'languages', 'get').mockReturnValue(['ca']);
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const session = { user, refresh: vi.fn().mockResolvedValue(user), signOut: vi.fn() };
  render(
    <ThemeProvider>
      <LanguageProvider>
        <NotificationProvider>
          <CurrentUserContext value={session}>
            <RouterProvider router={router} />
          </CurrentUserContext>
        </NotificationProvider>
      </LanguageProvider>
    </ThemeProvider>,
  );
  return { router, session };
}

// A work as GET /catalog/items gives it
export function makeItem(values = {}) {
  return {
    id: 'i-aloma',
    kind: 'book',
    title: 'Aloma',
    creator: 'Mercè Rodoreda',
    year: 1938,
    copies: 2,
    available: 1,
    cover: null,
    ...values,
  };
}

// An answer of axios
export const answer = (data) => Promise.resolve({ data });

// A failed request of axios with the backend's detail
export function failure(status, detail) {
  return Promise.reject(Object.assign(new Error(detail), { response: { status, data: { detail } } }));
}
