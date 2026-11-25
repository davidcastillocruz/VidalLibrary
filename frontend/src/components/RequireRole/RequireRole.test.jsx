import { screen } from '@testing-library/react';
import { afterEach, describe, expect, test, vi } from 'vitest';

import { LIBRARIAN, READER, renderPage } from '@/test/renderPage';

import RequireRole from './RequireRole';

const routes = [
  { path: '/login', element: <p>login</p> },
  { element: <RequireRole />, children: [{ path: '/loans', element: <p>my loans</p> }] },
  { element: <RequireRole role="librarian" />, children: [{ path: '/admin', element: <p>management</p> }] },
];

afterEach(() => {
  vi.restoreAllMocks();
});

describe('RequireRole', () => {
  test('a guest goes to sign in, remembering where it was going', () => {
    const { router } = renderPage(routes, { path: '/loans' });

    expect(screen.getByText('login')).toBeTruthy();
    expect(router.state.location.state).toEqual({ from: '/loans' });
  });

  test('a reader has its loans', () => {
    renderPage(routes, { path: '/loans', user: READER });
    expect(screen.getByText('my loans')).toBeTruthy();
  });

  test('a reader finds no management', () => {
    renderPage(routes, { path: '/admin', user: READER });
    expect(screen.getByText('Aquest volum no és al prestatge')).toBeTruthy();
  });

  test('a librarian opens the management', () => {
    renderPage(routes, { path: '/admin', user: LIBRARIAN });
    expect(screen.getByText('management')).toBeTruthy();
  });
});
